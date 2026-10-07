// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/*
 * Foundry fork tests for ArbitrageExecutor.
 *
 * These are NOT runnable without Foundry + an archive RPC. On your machine:
 *   1. forge init arb && cd arb
 *   2. copy ../ArbitrageExecutor.sol into src/ and this file into test/
 *   3. export MAINNET_RPC="https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY"
 *   4. forge test -vvv
 *
 * What they prove: the contract borrows from the REAL Aave V3 pool, swaps on the
 * REAL Uniswap V2 / SushiSwap routers, and the loss-safe invariant actually
 * reverts bad trades. The test MANUFACTURES a price gap with a whale swap — that
 * proves the mechanics, NOT that such gaps are capturable in production. (They
 * usually aren't; that's the honest point of flashscan.)
 */

import "forge-std/Test.sol";
import "../ArbitrageExecutor.sol";

interface IWETH {
    function deposit() external payable;
    function approve(address, uint256) external returns (bool);
    function balanceOf(address) external view returns (uint256);
}

interface IRouter {
    function swapExactTokensForTokens(uint256, uint256, address[] calldata, address, uint256)
        external returns (uint256[] memory);
    function getAmountsOut(uint256, address[] calldata) external view returns (uint256[] memory);
}

contract ArbitrageExecutorTest is Test {
    address constant AAVE = 0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2;
    address constant WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address constant USDC = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;
    address constant UNI = 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D;
    address constant SUSHI = 0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F;

    ArbitrageExecutor arb;

    function setUp() public {
        vm.createSelectFork(vm.envString("MAINNET_RPC"));
        address[] memory routers = new address[](2);
        routers[0] = UNI; routers[1] = SUSHI;
        address[] memory tokens = new address[](2);
        tokens[0] = WETH; tokens[1] = USDC;
        arb = new ArbitrageExecutor(AAVE, address(this), routers, tokens);
        arb.setMinProfitBps(1);
    }

    function _quote(address router, uint256 amt, address a, address b) internal view returns (uint256) {
        address[] memory path = new address[](2);
        path[0] = a; path[1] = b;
        uint256[] memory out = IRouter(router).getAmountsOut(amt, path);
        return out[out.length - 1];
    }

    // Whale dumps WETH on Uniswap -> WETH cheaper on Uni than Sushi -> arb window.
    function _makeDislocation(uint256 wethAmt) internal {
        vm.deal(address(this), wethAmt + 1 ether);
        IWETH(WETH).deposit{value: wethAmt}();
        IWETH(WETH).approve(UNI, wethAmt);
        address[] memory path = new address[](2);
        path[0] = WETH; path[1] = USDC;
        IRouter(UNI).swapExactTokensForTokens(wethAmt, 0, path, address(this), block.timestamp + 60);
    }

    function _hops(uint256 flashUsdc) internal view returns (ArbitrageExecutor.Hop[] memory hops) {
        uint256 q1 = _quote(UNI, flashUsdc, USDC, WETH);
        uint256 q2 = _quote(SUSHI, q1, WETH, USDC);
        hops = new ArbitrageExecutor.Hop[](2);
        hops[0] = ArbitrageExecutor.Hop(UNI, USDC, WETH, q1 * 99 / 100);
        hops[1] = ArbitrageExecutor.Hop(SUSHI, WETH, USDC, q2 * 99 / 100);
    }

    function test_profitableArbSucceeds() public {
        _makeDislocation(1_000 ether);
        uint256 flash = 20_000e6;
        uint256 before = IERC20(USDC).balanceOf(address(arb));
        arb.startArbitrage(USDC, flash, _hops(flash));
        uint256 got = IERC20(USDC).balanceOf(address(arb)) - before;
        assertGt(got, 0, "profit must remain on the contract");
    }

    function test_lossSafeInvariantReverts() public {
        _makeDislocation(1_000 ether);
        uint256 flash = 20_000e6;
        arb.setMinProfitBps(9_000); // demand 90% profit — impossible
        vm.expectRevert(); // NotProfitable
        arb.startArbitrage(USDC, flash, _hops(flash));
    }

    function test_unauthorizedReverts() public {
        uint256 flash = 20_000e6;
        vm.prank(address(0xBAD));
        vm.expectRevert(ArbitrageExecutor.NotAuthorized.selector);
        arb.startArbitrage(USDC, flash, _hops(flash));
    }

    function test_nonWhitelistedRouterReverts() public {
        uint256 flash = 20_000e6;
        ArbitrageExecutor.Hop[] memory hops = _hops(flash);
        hops[0].router = address(0xDEAD);
        vm.expectRevert();
        arb.startArbitrage(USDC, flash, hops);
    }
}
