// SPDX-License-Identifier: MIT
pragma solidity ^0.8;

interface IProxy {
    function getProxyOwner() external view returns (address);

    function setProxyOwner(address) external;
}
