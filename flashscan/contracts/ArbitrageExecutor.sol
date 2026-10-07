// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/*
 * ArbitrageExecutor — honest, loss-safe flash-loan arbitrage executor.
 *
 * WHAT IT IS
 *   An Aave V3 flash-loan receiver that runs a whitelisted sequence of
 *   Uniswap-V2-style swaps and keeps the profit on the contract. The whole
 *   trade is ONE atomic transaction: borrow -> swap -> repay. If the route
 *   does not end with at least `minProfitBps` more of the borrowed asset than
 *   it started with (after repaying the loan + Aave premium), the final check
 *   reverts and the ENTIRE transaction unwinds. You cannot be left holding a
 *   loss — the worst case is a reverted tx that cost only gas.
 *
 * WHAT IT IS NOT
 *   This is not a money printer. It can only EXECUTE a route you (your keeper)
 *   hand it after off-chain simulation. It does not find opportunities, and it
 *   does not win the searcher race — see flashscan/execution/README.md. On
 *   mainnet most attempts will revert (no edge) or lose the race; that is the
 *   system working correctly, not failing.
 *
 * SECURITY MODEL
 *   1. Only owner/executor can start a trade.
 *   2. Only whitelisted routers and tokens may appear in a route.
 *   3. The route must start and end on the borrowed asset.
 *   4. Each hop enforces a minimum output (slippage bound).
 *   5. FINAL TRUTH: endingBalance >= balanceBefore + amount + premium +
 *      minProfitAbs, or revert. This is the loss-safe invariant.
 *   6. The Aave callback is authenticated (caller == pool, initiator == self,
 *      a loan is open, and the params hash matches) instead of using a
 *      reentrancy guard on the callback — Aave invokes the callback INSIDE the
 *      startArbitrage transaction, so a guard there would always revert.
 *   7. No native ETH is accepted.
 */

interface IERC20 {
    function balanceOf(address a) external view returns (uint256);
    function transfer(address to, uint256 v) external returns (bool);
    function approve(address s, uint256 v) external returns (bool);
}

interface IAavePool {
    function flashLoanSimple(
        address receiver,
        address asset,
        uint256 amount,
        bytes calldata params,
        uint16 referralCode
    ) external;
    function FLASHLOAN_PREMIUM_TOTAL() external view returns (uint128);
}

interface IFlashLoanSimpleReceiver {
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external returns (bool);
}

interface IUniswapV2Router {
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);
}

abstract contract ReentrancyGuard {
    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED = 2;
    uint256 private _status = _NOT_ENTERED;
    error Reentrancy();
    modifier nonReentrant() {
        if (_status == _ENTERED) revert Reentrancy();
        _status = _ENTERED;
        _;
        _status = _NOT_ENTERED;
    }
}

contract ArbitrageExecutor is IFlashLoanSimpleReceiver, ReentrancyGuard {
    // --- Types --------------------------------------------------------------
    struct Hop {
        address router;   // whitelisted V2 router
        address tokenIn;
        address tokenOut;
        uint256 minOut;   // slippage floor for this hop
    }

    // --- Errors -------------------------------------------------------------
    error NotAuthorized();
    error Paused();
    error ZeroAddress();
    error ZeroAmount();
    error BadCallback();
    error LoanAlreadyOpen();
    error RouterNotWhitelisted(address router);
    error TokenNotWhitelisted(address token);
    error BadRouteShape();
    error HopMinOutZero();
    error NotProfitable(uint256 ending, uint256 required);
    error NativeDisabled();
    error MinProfitTooHigh();

    // --- Constants ----------------------------------------------------------
    uint256 public constant BPS = 10_000;
    uint256 public constant MIN_HOPS = 2;
    uint256 public constant MAX_HOPS = 6;
    uint256 public constant SWAP_DEADLINE_WINDOW = 5 minutes;

    // --- Immutable ----------------------------------------------------------
    address public immutable owner;
    address public immutable aavePool;

    // --- Config -------------------------------------------------------------
    address public executor;
    bool public paused;
    uint256 public minProfitBps = 10; // 0.10% default floor over debt. Owner-tunable.
    mapping(address => bool) public routerWhitelist;
    mapping(address => bool) public tokenWhitelist;

    // --- Transient loan state ----------------------------------------------
    bool public loanOpen;
    bytes32 private _activeParamsHash;
    address private _activeAsset;
    uint256 private _activeAmount;
    uint256 private _balanceBefore;

    // --- Events -------------------------------------------------------------
    event ExecutorUpdated(address indexed executor);
    event PausedSet(bool paused);
    event MinProfitBpsSet(uint256 bps);
    event RouterSet(address indexed router, bool allowed);
    event TokenSet(address indexed token, bool allowed);
    event HopDone(uint256 indexed i, address router, address tokenIn, address tokenOut, uint256 amountIn, uint256 amountOut);
    event ArbCompleted(address indexed asset, uint256 amount, uint256 premium, uint256 profit);
    event Withdrawn(address indexed token, address indexed to, uint256 amount);

    // --- Modifiers ----------------------------------------------------------
    modifier onlyOwner() {
        if (msg.sender != owner) revert NotAuthorized();
        _;
    }
    modifier onlyExecutorOrOwner() {
        if (msg.sender != executor && msg.sender != owner) revert NotAuthorized();
        _;
    }

    constructor(address pool_, address executor_, address[] memory routers, address[] memory tokens) {
        if (pool_ == address(0)) revert ZeroAddress();
        owner = msg.sender;
        aavePool = pool_;
        executor = executor_ == address(0) ? msg.sender : executor_;
        for (uint256 i; i < routers.length; ++i) _setRouter(routers[i], true);
        for (uint256 i; i < tokens.length; ++i) _setToken(tokens[i], true);
    }

    // --- Admin --------------------------------------------------------------
    function setExecutor(address e) external onlyOwner {
        if (e == address(0)) revert ZeroAddress();
        executor = e;
        emit ExecutorUpdated(e);
    }
    function setPaused(bool p) external onlyOwner {
        paused = p;
        emit PausedSet(p);
    }
    function setMinProfitBps(uint256 bps) external onlyOwner {
        if (bps >= BPS) revert MinProfitTooHigh();
        minProfitBps = bps;
        emit MinProfitBpsSet(bps);
    }
    function setRouter(address r, bool a) external onlyOwner { _setRouter(r, a); }
    function setToken(address t, bool a) external onlyOwner { _setToken(t, a); }

    /// @notice Withdraw accumulated profit (or any token) to `to`.
    function withdraw(address token, address to, uint256 amount) external onlyOwner {
        if (to == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();
        _safeTransfer(token, to, amount);
        emit Withdrawn(token, to, amount);
    }

    // --- Core: start a flash-loan arb --------------------------------------
    /// @param asset  borrowed asset (must be whitelisted; route starts/ends here)
    /// @param amount flash-loan size
    /// @param hops   whitelisted V2 swap route, asset -> ... -> asset
    function startArbitrage(address asset, uint256 amount, Hop[] calldata hops)
        external
        onlyExecutorOrOwner
        nonReentrant
    {
        if (paused) revert Paused();
        if (asset == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();
        if (loanOpen) revert LoanAlreadyOpen();
        if (!tokenWhitelist[asset]) revert TokenNotWhitelisted(asset);
        _validateRoute(asset, hops);

        bytes memory params = abi.encode(asset, amount, hops);
        loanOpen = true;
        _activeAsset = asset;
        _activeAmount = amount;
        _activeParamsHash = keccak256(params);
        _balanceBefore = IERC20(asset).balanceOf(address(this));

        IAavePool(aavePool).flashLoanSimple(address(this), asset, amount, params, 0);

        // Aave invokes executeOperation synchronously above; it must close the loan.
        if (loanOpen) revert BadCallback();
    }

    // --- Aave callback ------------------------------------------------------
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external override returns (bool) {
        // Authenticate the callback (no reentrancy guard here — see header).
        if (msg.sender != aavePool) revert BadCallback();
        if (initiator != address(this)) revert BadCallback();
        if (!loanOpen) revert BadCallback();
        if (asset != _activeAsset || amount != _activeAmount) revert BadCallback();
        if (keccak256(params) != _activeParamsHash) revert BadCallback();

        (, , Hop[] memory hops) = abi.decode(params, (address, uint256, Hop[]));

        // Confirm the borrowed funds arrived.
        uint256 have = IERC20(asset).balanceOf(address(this));
        require(have >= _balanceBefore + amount, "loan not received");

        _runHops(hops);

        // FINAL TRUTH: loss-safe invariant.
        uint256 ending = IERC20(asset).balanceOf(address(this));
        uint256 debt = amount + premium;
        uint256 minProfitAbs = (amount * minProfitBps) / BPS;
        uint256 required = _balanceBefore + debt + minProfitAbs;
        if (ending < required) revert NotProfitable(ending, required);

        uint256 profit = ending - _balanceBefore - debt;

        // Approve the pool to pull back principal + premium.
        _safeApprove(asset, aavePool, debt);

        // Reset transient state before returning control to the pool.
        loanOpen = false;
        _activeAsset = address(0);
        _activeAmount = 0;
        _activeParamsHash = bytes32(0);
        _balanceBefore = 0;

        emit ArbCompleted(asset, amount, premium, profit);
        return true;
    }

    // --- Internals ----------------------------------------------------------
    function _runHops(Hop[] memory hops) internal {
        uint256 amountIn = _activeAmount; // first hop spends the borrowed amount
        for (uint256 i; i < hops.length; ++i) {
            Hop memory h = hops[i];
            address[] memory path = new address[](2);
            path[0] = h.tokenIn;
            path[1] = h.tokenOut;

            _safeApprove(h.tokenIn, h.router, amountIn);
            uint256[] memory outs = IUniswapV2Router(h.router).swapExactTokensForTokens(
                amountIn, h.minOut, path, address(this), block.timestamp + SWAP_DEADLINE_WINDOW
            );
            _safeApprove(h.tokenIn, h.router, 0); // reset approval

            uint256 got = outs[outs.length - 1];
            emit HopDone(i, h.router, h.tokenIn, h.tokenOut, amountIn, got);
            amountIn = got; // chain into the next hop
        }
    }

    function _validateRoute(address asset, Hop[] calldata hops) internal view {
        uint256 n = hops.length;
        if (n < MIN_HOPS || n > MAX_HOPS) revert BadRouteShape();
        if (hops[0].tokenIn != asset || hops[n - 1].tokenOut != asset) revert BadRouteShape();
        for (uint256 i; i < n; ++i) {
            Hop calldata h = hops[i];
            if (!routerWhitelist[h.router]) revert RouterNotWhitelisted(h.router);
            if (!tokenWhitelist[h.tokenIn]) revert TokenNotWhitelisted(h.tokenIn);
            if (!tokenWhitelist[h.tokenOut]) revert TokenNotWhitelisted(h.tokenOut);
            if (h.minOut == 0) revert HopMinOutZero();
            if (i + 1 < n && h.tokenOut != hops[i + 1].tokenIn) revert BadRouteShape();
        }
    }

    function _setRouter(address r, bool a) internal {
        if (r == address(0)) revert ZeroAddress();
        routerWhitelist[r] = a;
        emit RouterSet(r, a);
    }
    function _setToken(address t, bool a) internal {
        if (t == address(0)) revert ZeroAddress();
        tokenWhitelist[t] = a;
        emit TokenSet(t, a);
    }

    // Minimal safe ERC20 helpers (tolerate non-standard no-return tokens).
    function _safeApprove(address token, address spender, uint256 value) internal {
        (bool ok, bytes memory ret) = token.call(abi.encodeWithSelector(IERC20.approve.selector, spender, value));
        require(ok && (ret.length == 0 || abi.decode(ret, (bool))), "approve failed");
    }
    function _safeTransfer(address token, address to, uint256 value) internal {
        (bool ok, bytes memory ret) = token.call(abi.encodeWithSelector(IERC20.transfer.selector, to, value));
        require(ok && (ret.length == 0 || abi.decode(ret, (bool))), "transfer failed");
    }

    // --- No native ETH ------------------------------------------------------
    receive() external payable { revert NativeDisabled(); }
    fallback() external payable { revert NativeDisabled(); }
}
