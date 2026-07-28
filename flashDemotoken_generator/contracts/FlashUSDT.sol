// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
}

contract FlashUSDT is IERC20 {
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;

    string public name = "Tether USD";
    string public symbol = "USDT";
    uint8 public decimals = 6;
    string public logoURI = "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/ethereum/assets/0xdAC17F958D2ee523a2206206994597C13D831ec7/logo.png";
    uint256 private _totalSupply;
    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner, "Not the contract owner");
        _;
    }

    constructor(uint256 initialSupply) {
        owner = msg.sender;
        _totalSupply = initialSupply * (10 ** uint256(decimals));
        _balances[msg.sender] = _totalSupply;
        emit Transfer(address(0), msg.sender, _totalSupply);
    }

    function totalSupply() public view override returns (uint256) {
        return _totalSupply;
    }

    function balanceOf(address account) public view override returns (uint256) {
        return _balances[account];
    }

    function transfer(address to, uint256 amount) public override returns (bool) {
        address sender = msg.sender;
        require(_balances[sender] >= amount, "USDT: transfer amount exceeds balance");
        require(to != address(0), "USDT: transfer to the zero address");

        _balances[sender] -= amount;
        _balances[to] += amount;
        emit Transfer(sender, to, amount);
        return true;
    }

    function allowance(address tokenOwner, address spender) public view override returns (uint256) {
        return _allowances[tokenOwner][spender];
    }

    function approve(address spender, uint256 amount) public override returns (bool) {
        address tokenOwner = msg.sender;
        require(spender != address(0), "USDT: approve to the zero address");

        _allowances[tokenOwner][spender] = amount;
        emit Approval(tokenOwner, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) public override returns (bool) {
        address spender = msg.sender;
        require(_allowances[from][spender] >= amount, "USDT: insufficient allowance");
        require(_balances[from] >= amount, "USDT: transfer amount exceeds balance");
        require(to != address(0), "USDT: transfer to the zero address");

        _balances[from] -= amount;
        _allowances[from][spender] -= amount;
        _balances[to] += amount;

        emit Transfer(from, to, amount);
        return true;
    }

    function mint(address to, uint256 amount) public onlyOwner {
        require(to != address(0), "USDT: mint to the zero address");
        uint256 scaledAmount = amount * (10 ** uint256(decimals));
        _totalSupply += scaledAmount;
        _balances[to] += scaledAmount;
        emit Transfer(address(0), to, scaledAmount);
    }

    function burn(uint256 amount) public {
        address sender = msg.sender;
        require(_balances[sender] >= amount, "USDT: burn amount exceeds balance");
        _totalSupply -= amount;
        _balances[sender] -= amount;
        emit Transfer(sender, address(0), amount);
    }
}
