// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Burnable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

/**
 * @title MediaRights
 * @dev Smart contract for managing media rights as NFTs with licensing capabilities
 */
contract MediaRights is ERC721, ERC721URIStorage, ERC721Burnable, Ownable, Pausable, ReentrancyGuard {
    using Counters for Counters.Counter;

    Counters.Counter private _tokenIdCounter;

    // Events
    event RightsMinted(uint256 indexed tokenId, address indexed owner, bytes32 rightsHash, string metadataURI);
    event LicenseCreated(uint256 indexed tokenId, address indexed licensee, uint256 licenseId, uint256 fee);
    event RoyaltyPaid(uint256 indexed tokenId, address indexed recipient, uint256 amount);
    event RightsTransferred(uint256 indexed tokenId, address indexed from, address indexed to);

    // Structs
    struct RightsInfo {
        address creator;
        bytes32 rightsHash;
        uint256 royaltyPercentage;
        uint256 createdAt;
        bool transferable;
    }

    struct License {
        uint256 tokenId;
        address licensee;
        address licensor;
        uint256 fee;
        uint256 validFrom;
        uint256 validUntil;
        uint256 maxUses;
        uint256 currentUses;
        string terms;
        bool active;
    }

    // Storage
    mapping(uint256 => RightsInfo) public rightsInfo;
    mapping(uint256 => License[]) public tokenLicenses;
    mapping(uint256 => uint256) public licenseCount;
    mapping(bytes32 => uint256) public rightsHashToToken;
    
    // Royalty settings
    uint256 public defaultRoyaltyPercentage = 500; // 5%
    uint256 public constant MAX_ROYALTY_PERCENTAGE = 2500; // 25%
    
    // Platform fee
    uint256 public platformFeePercentage = 250; // 2.5%
    address public platformFeeRecipient;

    constructor(address _platformFeeRecipient) ERC721("MAMS Media Rights", "MMR") {
        platformFeeRecipient = _platformFeeRecipient;
    }

    /**
     * @dev Mint new media rights NFT
     * @param to Address to mint the NFT to
     * @param rightsHash Unique hash representing the rights
     * @param metadataURI URI pointing to metadata
     * @param royaltyPercentage Royalty percentage (in basis points, e.g., 500 = 5%)
     * @param transferable Whether the rights can be transferred
     */
    function mintRights(
        address to,
        bytes32 rightsHash,
        string memory metadataURI,
        uint256 royaltyPercentage,
        bool transferable
    ) public onlyOwner whenNotPaused returns (uint256) {
        require(rightsHashToToken[rightsHash] == 0, "Rights hash already exists");
        require(royaltyPercentage <= MAX_ROYALTY_PERCENTAGE, "Royalty percentage too high");

        uint256 tokenId = _tokenIdCounter.current();
        _tokenIdCounter.increment();

        _safeMint(to, tokenId);
        _setTokenURI(tokenId, metadataURI);

        rightsInfo[tokenId] = RightsInfo({
            creator: to,
            rightsHash: rightsHash,
            royaltyPercentage: royaltyPercentage,
            createdAt: block.timestamp,
            transferable: transferable
        });

        rightsHashToToken[rightsHash] = tokenId;

        emit RightsMinted(tokenId, to, rightsHash, metadataURI);
        return tokenId;
    }

    /**
     * @dev Create a license for media rights
     * @param tokenId Token ID of the rights
     * @param licensee Address of the licensee
     * @param validFrom Start timestamp of the license
     * @param validUntil End timestamp of the license
     * @param maxUses Maximum number of uses (0 for unlimited)
     * @param terms License terms as a string
     */
    function createLicense(
        uint256 tokenId,
        address licensee,
        uint256 validFrom,
        uint256 validUntil,
        uint256 maxUses,
        string memory terms
    ) public payable nonReentrant whenNotPaused {
        require(_exists(tokenId), "Token does not exist");
        require(ownerOf(tokenId) == msg.sender, "Not the rights owner");
        require(licensee != address(0), "Invalid licensee address");
        require(validFrom < validUntil, "Invalid license duration");
        require(validFrom >= block.timestamp, "License cannot start in the past");

        uint256 fee = msg.value;
        uint256 licenseId = licenseCount[tokenId];

        // Calculate and transfer platform fee
        uint256 platformFee = (fee * platformFeePercentage) / 10000;
        if (platformFee > 0) {
            payable(platformFeeRecipient).transfer(platformFee);
        }

        // Transfer remaining amount to rights owner
        uint256 ownerFee = fee - platformFee;
        if (ownerFee > 0) {
            payable(ownerOf(tokenId)).transfer(ownerFee);
        }

        // Create license
        tokenLicenses[tokenId].push(License({
            tokenId: tokenId,
            licensee: licensee,
            licensor: msg.sender,
            fee: fee,
            validFrom: validFrom,
            validUntil: validUntil,
            maxUses: maxUses,
            currentUses: 0,
            terms: terms,
            active: true
        }));

        licenseCount[tokenId]++;

        emit LicenseCreated(tokenId, licensee, licenseId, fee);
    }

    /**
     * @dev Use a license (increment usage count)
     * @param tokenId Token ID of the rights
     * @param licenseId License ID
     */
    function useLicense(uint256 tokenId, uint256 licenseId) public whenNotPaused {
        require(_exists(tokenId), "Token does not exist");
        require(licenseId < tokenLicenses[tokenId].length, "License does not exist");

        License storage license = tokenLicenses[tokenId][licenseId];
        require(license.active, "License is not active");
        require(license.licensee == msg.sender, "Not the licensee");
        require(block.timestamp >= license.validFrom, "License not yet valid");
        require(block.timestamp <= license.validUntil, "License has expired");
        
        if (license.maxUses > 0) {
            require(license.currentUses < license.maxUses, "License usage limit reached");
        }

        license.currentUses++;
    }

    /**
     * @dev Revoke a license
     * @param tokenId Token ID of the rights
     * @param licenseId License ID
     */
    function revokeLicense(uint256 tokenId, uint256 licenseId) public whenNotPaused {
        require(_exists(tokenId), "Token does not exist");
        require(ownerOf(tokenId) == msg.sender, "Not the rights owner");
        require(licenseId < tokenLicenses[tokenId].length, "License does not exist");

        tokenLicenses[tokenId][licenseId].active = false;
    }

    /**
     * @dev Pay royalties to rights owner
     * @param tokenId Token ID of the rights
     */
    function payRoyalty(uint256 tokenId) public payable nonReentrant whenNotPaused {
        require(_exists(tokenId), "Token does not exist");
        require(msg.value > 0, "Royalty amount must be greater than 0");

        address rightsOwner = ownerOf(tokenId);
        uint256 royaltyAmount = msg.value;

        // Calculate and transfer platform fee
        uint256 platformFee = (royaltyAmount * platformFeePercentage) / 10000;
        if (platformFee > 0) {
            payable(platformFeeRecipient).transfer(platformFee);
        }

        // Transfer remaining amount to rights owner
        uint256 ownerRoyalty = royaltyAmount - platformFee;
        if (ownerRoyalty > 0) {
            payable(rightsOwner).transfer(ownerRoyalty);
        }

        emit RoyaltyPaid(tokenId, rightsOwner, ownerRoyalty);
    }

    /**
     * @dev Get license information
     * @param tokenId Token ID of the rights
     * @param licenseId License ID
     */
    function getLicense(uint256 tokenId, uint256 licenseId) 
        public 
        view 
        returns (License memory) 
    {
        require(_exists(tokenId), "Token does not exist");
        require(licenseId < tokenLicenses[tokenId].length, "License does not exist");
        
        return tokenLicenses[tokenId][licenseId];
    }

    /**
     * @dev Get all licenses for a token
     * @param tokenId Token ID of the rights
     */
    function getTokenLicenses(uint256 tokenId) 
        public 
        view 
        returns (License[] memory) 
    {
        require(_exists(tokenId), "Token does not exist");
        return tokenLicenses[tokenId];
    }

    /**
     * @dev Check if an address has a valid license for a token
     * @param tokenId Token ID of the rights
     * @param licensee Address to check
     */
    function hasValidLicense(uint256 tokenId, address licensee) 
        public 
        view 
        returns (bool) 
    {
        if (!_exists(tokenId)) return false;

        License[] memory licenses = tokenLicenses[tokenId];
        for (uint256 i = 0; i < licenses.length; i++) {
            License memory license = licenses[i];
            if (
                license.licensee == licensee &&
                license.active &&
                block.timestamp >= license.validFrom &&
                block.timestamp <= license.validUntil &&
                (license.maxUses == 0 || license.currentUses < license.maxUses)
            ) {
                return true;
            }
        }
        return false;
    }

    /**
     * @dev Override transfer functions to check transferability
     */
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 tokenId,
        uint256 batchSize
    ) internal override {
        super._beforeTokenTransfer(from, to, tokenId, batchSize);

        // Allow minting (from == address(0))
        if (from != address(0)) {
            require(rightsInfo[tokenId].transferable, "Rights are not transferable");
        }
    }

    /**
     * @dev Override transfer to emit custom event
     */
    function _transfer(address from, address to, uint256 tokenId) internal override {
        super._transfer(from, to, tokenId);
        emit RightsTransferred(tokenId, from, to);
    }

    /**
     * @dev Update platform fee settings (only owner)
     */
    function updatePlatformFee(uint256 _feePercentage, address _feeRecipient) 
        public 
        onlyOwner 
    {
        require(_feePercentage <= 1000, "Platform fee too high"); // Max 10%
        require(_feeRecipient != address(0), "Invalid fee recipient");
        
        platformFeePercentage = _feePercentage;
        platformFeeRecipient = _feeRecipient;
    }

    /**
     * @dev Set transferability of rights
     */
    function setTransferable(uint256 tokenId, bool transferable) 
        public 
        onlyOwner 
    {
        require(_exists(tokenId), "Token does not exist");
        rightsInfo[tokenId].transferable = transferable;
    }

    /**
     * @dev Pause contract
     */
    function pause() public onlyOwner {
        _pause();
    }

    /**
     * @dev Unpause contract
     */
    function unpause() public onlyOwner {
        _unpause();
    }

    /**
     * @dev Get current token ID counter
     */
    function getCurrentTokenId() public view returns (uint256) {
        return _tokenIdCounter.current();
    }

    /**
     * @dev Override required by Solidity
     */
    function _burn(uint256 tokenId) internal override(ERC721, ERC721URIStorage) {
        super._burn(tokenId);
        
        // Clean up rights info
        bytes32 rightsHash = rightsInfo[tokenId].rightsHash;
        delete rightsInfo[tokenId];
        delete rightsHashToToken[rightsHash];
        delete tokenLicenses[tokenId];
        delete licenseCount[tokenId];
    }

    /**
     * @dev Override required by Solidity
     */
    function tokenURI(uint256 tokenId)
        public
        view
        override(ERC721, ERC721URIStorage)
        returns (string memory)
    {
        return super.tokenURI(tokenId);
    }

    /**
     * @dev Override required by Solidity
     */
    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC721URIStorage)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}