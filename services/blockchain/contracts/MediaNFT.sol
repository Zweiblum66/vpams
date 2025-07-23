// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Burnable.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Royalty.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title MediaNFT
 * @dev Comprehensive NFT contract for media assets with marketplace functionality
 */
contract MediaNFT is 
    ERC721, 
    ERC721URIStorage, 
    ERC721Burnable, 
    ERC721Royalty,
    Ownable, 
    Pausable, 
    ReentrancyGuard 
{
    using Counters for Counters.Counter;
    using Strings for uint256;

    Counters.Counter private _tokenIdCounter;

    // Events
    event NFTMinted(uint256 indexed tokenId, address indexed owner, string tokenURI, uint96 royaltyFee);
    event NFTListed(uint256 indexed tokenId, address indexed seller, uint256 price, uint256 endTime);
    event NFTSold(uint256 indexed tokenId, address indexed buyer, address indexed seller, uint256 price);
    event BidPlaced(uint256 indexed tokenId, address indexed bidder, uint256 bidAmount);
    event BidAccepted(uint256 indexed tokenId, address indexed bidder, uint256 bidAmount);
    event ListingCancelled(uint256 indexed tokenId, address indexed seller);
    event RoyaltyUpdated(uint256 indexed tokenId, address recipient, uint96 feeNumerator);

    // Structs
    struct Listing {
        uint256 tokenId;
        address seller;
        uint256 price;
        uint256 startTime;
        uint256 endTime;
        bool active;
        AuctionType auctionType;
        uint256 reservePrice;
    }

    struct Bid {
        uint256 tokenId;
        address bidder;
        uint256 amount;
        uint256 timestamp;
        uint256 expiresAt;
        bool active;
    }

    struct TokenInfo {
        address creator;
        uint256 createdAt;
        string category;
        string[] tags;
        bool transferable;
        bytes32 contentHash;
    }

    enum AuctionType {
        FIXED_PRICE,
        ENGLISH_AUCTION,
        DUTCH_AUCTION,
        RESERVE_AUCTION
    }

    // Storage
    mapping(uint256 => Listing) public listings;
    mapping(uint256 => Bid[]) public tokenBids;
    mapping(uint256 => TokenInfo) public tokenInfo;
    mapping(address => uint256[]) public userTokens;
    mapping(uint256 => uint256) public userTokenIndex;
    
    // Marketplace settings
    uint256 public marketplaceFeePercentage = 250; // 2.5%
    address public marketplaceFeeRecipient;
    uint256 public minimumBidIncrement = 0.01 ether;
    uint256 public maximumRoyalty = 1000; // 10%
    
    // Collection settings
    string public baseTokenURI;
    uint256 public maxSupply;
    bool public publicMintEnabled = false;
    uint256 public mintPrice = 0.1 ether;
    
    constructor(
        string memory name,
        string memory symbol,
        address _marketplaceFeeRecipient,
        uint256 _maxSupply
    ) ERC721(name, symbol) {
        marketplaceFeeRecipient = _marketplaceFeeRecipient;
        maxSupply = _maxSupply;
    }

    /**
     * @dev Mint new NFT with metadata and royalty
     * @param to Address to mint the NFT to
     * @param tokenURI URI pointing to metadata
     * @param royaltyRecipient Address to receive royalties
     * @param royaltyFeeNumerator Royalty fee in basis points (e.g., 500 = 5%)
     * @param category NFT category
     * @param tags Array of tags
     * @param transferable Whether the NFT can be transferred
     * @param contentHash Hash of the content for verification
     */
    function mint(
        address to,
        string memory tokenURI,
        address royaltyRecipient,
        uint96 royaltyFeeNumerator,
        string memory category,
        string[] memory tags,
        bool transferable,
        bytes32 contentHash
    ) public onlyOwner whenNotPaused returns (uint256) {
        require(royaltyFeeNumerator <= maximumRoyalty, "Royalty too high");
        require(maxSupply == 0 || _tokenIdCounter.current() < maxSupply, "Max supply reached");

        uint256 tokenId = _tokenIdCounter.current();
        _tokenIdCounter.increment();

        _safeMint(to, tokenId);
        _setTokenURI(tokenId, tokenURI);
        
        if (royaltyFeeNumerator > 0) {
            _setTokenRoyalty(tokenId, royaltyRecipient, royaltyFeeNumerator);
        }

        // Store token info
        tokenInfo[tokenId] = TokenInfo({
            creator: to,
            createdAt: block.timestamp,
            category: category,
            tags: tags,
            transferable: transferable,
            contentHash: contentHash
        });

        // Update user tokens
        userTokens[to].push(tokenId);
        userTokenIndex[tokenId] = userTokens[to].length - 1;

        emit NFTMinted(tokenId, to, tokenURI, royaltyFeeNumerator);
        return tokenId;
    }

    /**
     * @dev Public mint function (if enabled)
     */
    function publicMint(
        string memory tokenURI,
        address royaltyRecipient,
        uint96 royaltyFeeNumerator,
        string memory category,
        string[] memory tags,
        bytes32 contentHash
    ) public payable whenNotPaused nonReentrant returns (uint256) {
        require(publicMintEnabled, "Public minting disabled");
        require(msg.value >= mintPrice, "Insufficient payment");
        require(maxSupply == 0 || _tokenIdCounter.current() < maxSupply, "Max supply reached");

        uint256 tokenId = mint(
            msg.sender,
            tokenURI,
            royaltyRecipient,
            royaltyFeeNumerator,
            category,
            tags,
            true, // Public mints are transferable
            contentHash
        );

        // Send payment to contract owner
        if (msg.value > 0) {
            payable(owner()).transfer(msg.value);
        }

        return tokenId;
    }

    /**
     * @dev List NFT for sale
     */
    function listForSale(
        uint256 tokenId,
        uint256 price,
        uint256 duration,
        AuctionType auctionType,
        uint256 reservePrice
    ) public whenNotPaused {
        require(_exists(tokenId), "Token does not exist");
        require(ownerOf(tokenId) == msg.sender || getApproved(tokenId) == msg.sender, "Not owner or approved");
        require(price > 0, "Price must be greater than 0");
        require(duration > 0, "Duration must be greater than 0");
        require(!listings[tokenId].active, "Already listed");

        if (auctionType == AuctionType.RESERVE_AUCTION) {
            require(reservePrice > 0, "Reserve price required");
        }

        uint256 endTime = block.timestamp + duration;

        listings[tokenId] = Listing({
            tokenId: tokenId,
            seller: msg.sender,
            price: price,
            startTime: block.timestamp,
            endTime: endTime,
            active: true,
            auctionType: auctionType,
            reservePrice: reservePrice
        });

        emit NFTListed(tokenId, msg.sender, price, endTime);
    }

    /**
     * @dev Buy NFT at fixed price
     */
    function buyNFT(uint256 tokenId) public payable whenNotPaused nonReentrant {
        Listing storage listing = listings[tokenId];
        require(listing.active, "Not listed for sale");
        require(block.timestamp <= listing.endTime, "Listing expired");
        require(listing.auctionType == AuctionType.FIXED_PRICE, "Not fixed price sale");
        require(msg.value >= listing.price, "Insufficient payment");

        address seller = listing.seller;
        address buyer = msg.sender;
        uint256 price = listing.price;

        // Mark listing as inactive
        listing.active = false;

        // Calculate fees
        (uint256 royaltyAmount, address royaltyRecipient) = royaltyInfo(tokenId, price);
        uint256 marketplaceFee = (price * marketplaceFeePercentage) / 10000;
        uint256 sellerAmount = price - royaltyAmount - marketplaceFee;

        // Transfer NFT
        _transfer(seller, buyer, tokenId);

        // Distribute payments
        if (royaltyAmount > 0 && royaltyRecipient != address(0)) {
            payable(royaltyRecipient).transfer(royaltyAmount);
        }
        if (marketplaceFee > 0) {
            payable(marketplaceFeeRecipient).transfer(marketplaceFee);
        }
        payable(seller).transfer(sellerAmount);

        // Refund excess payment
        if (msg.value > price) {
            payable(buyer).transfer(msg.value - price);
        }

        emit NFTSold(tokenId, buyer, seller, price);
    }

    /**
     * @dev Place bid on NFT
     */
    function placeBid(uint256 tokenId) public payable whenNotPaused nonReentrant {
        require(_exists(tokenId), "Token does not exist");
        require(msg.value > 0, "Bid must be greater than 0");
        
        Listing storage listing = listings[tokenId];
        require(listing.active, "Not listed for sale");
        require(block.timestamp <= listing.endTime, "Listing expired");
        require(listing.auctionType != AuctionType.FIXED_PRICE, "Use buyNFT for fixed price");

        // Check minimum bid increment
        Bid[] storage bids = tokenBids[tokenId];
        if (bids.length > 0) {
            uint256 highestBid = _getHighestBid(tokenId);
            require(msg.value >= highestBid + minimumBidIncrement, "Bid too low");
        } else {
            require(msg.value >= listing.price, "Bid below starting price");
        }

        // Store bid
        bids.push(Bid({
            tokenId: tokenId,
            bidder: msg.sender,
            amount: msg.value,
            timestamp: block.timestamp,
            expiresAt: listing.endTime,
            active: true
        }));

        emit BidPlaced(tokenId, msg.sender, msg.value);

        // Auto-accept if reserve price met (for reserve auctions)
        if (listing.auctionType == AuctionType.RESERVE_AUCTION && 
            msg.value >= listing.reservePrice) {
            _acceptBid(tokenId, bids.length - 1);
        }
    }

    /**
     * @dev Accept a bid (for seller)
     */
    function acceptBid(uint256 tokenId, uint256 bidIndex) public whenNotPaused nonReentrant {
        Listing storage listing = listings[tokenId];
        require(listing.active, "Not listed for sale");
        require(listing.seller == msg.sender, "Not the seller");

        _acceptBid(tokenId, bidIndex);
    }

    /**
     * @dev Internal function to accept a bid
     */
    function _acceptBid(uint256 tokenId, uint256 bidIndex) internal {
        Listing storage listing = listings[tokenId];
        Bid[] storage bids = tokenBids[tokenId];
        
        require(bidIndex < bids.length, "Invalid bid index");
        Bid storage acceptedBid = bids[bidIndex];
        require(acceptedBid.active, "Bid not active");

        address seller = listing.seller;
        address buyer = acceptedBid.bidder;
        uint256 price = acceptedBid.amount;

        // Mark listing and bid as inactive
        listing.active = false;
        acceptedBid.active = false;

        // Calculate fees
        (uint256 royaltyAmount, address royaltyRecipient) = royaltyInfo(tokenId, price);
        uint256 marketplaceFee = (price * marketplaceFeePercentage) / 10000;
        uint256 sellerAmount = price - royaltyAmount - marketplaceFee;

        // Transfer NFT
        _transfer(seller, buyer, tokenId);

        // Distribute payments
        if (royaltyAmount > 0 && royaltyRecipient != address(0)) {
            payable(royaltyRecipient).transfer(royaltyAmount);
        }
        if (marketplaceFee > 0) {
            payable(marketplaceFeeRecipient).transfer(marketplaceFee);
        }
        payable(seller).transfer(sellerAmount);

        // Refund other bidders
        for (uint256 i = 0; i < bids.length; i++) {
            if (i != bidIndex && bids[i].active) {
                bids[i].active = false;
                payable(bids[i].bidder).transfer(bids[i].amount);
            }
        }

        emit BidAccepted(tokenId, buyer, price);
        emit NFTSold(tokenId, buyer, seller, price);
    }

    /**
     * @dev Cancel listing
     */
    function cancelListing(uint256 tokenId) public whenNotPaused {
        Listing storage listing = listings[tokenId];
        require(listing.active, "Not listed");
        require(listing.seller == msg.sender, "Not the seller");

        listing.active = false;

        // Refund all bidders
        Bid[] storage bids = tokenBids[tokenId];
        for (uint256 i = 0; i < bids.length; i++) {
            if (bids[i].active) {
                bids[i].active = false;
                payable(bids[i].bidder).transfer(bids[i].amount);
            }
        }

        emit ListingCancelled(tokenId, msg.sender);
    }

    /**
     * @dev Withdraw expired bid
     */
    function withdrawBid(uint256 tokenId, uint256 bidIndex) public nonReentrant {
        Bid[] storage bids = tokenBids[tokenId];
        require(bidIndex < bids.length, "Invalid bid index");
        
        Bid storage bid = bids[bidIndex];
        require(bid.bidder == msg.sender, "Not your bid");
        require(bid.active, "Bid not active");
        require(block.timestamp > bid.expiresAt, "Bid not expired");

        bid.active = false;
        payable(msg.sender).transfer(bid.amount);
    }

    /**
     * @dev Get highest active bid for a token
     */
    function getHighestBid(uint256 tokenId) public view returns (uint256) {
        return _getHighestBid(tokenId);
    }

    function _getHighestBid(uint256 tokenId) internal view returns (uint256) {
        Bid[] storage bids = tokenBids[tokenId];
        uint256 highest = 0;
        
        for (uint256 i = 0; i < bids.length; i++) {
            if (bids[i].active && bids[i].amount > highest) {
                highest = bids[i].amount;
            }
        }
        
        return highest;
    }

    /**
     * @dev Get all active bids for a token
     */
    function getActiveBids(uint256 tokenId) public view returns (Bid[] memory) {
        Bid[] storage allBids = tokenBids[tokenId];
        uint256 activeCount = 0;
        
        // Count active bids
        for (uint256 i = 0; i < allBids.length; i++) {
            if (allBids[i].active) {
                activeCount++;
            }
        }
        
        // Create array of active bids
        Bid[] memory activeBids = new Bid[](activeCount);
        uint256 index = 0;
        
        for (uint256 i = 0; i < allBids.length; i++) {
            if (allBids[i].active) {
                activeBids[index] = allBids[i];
                index++;
            }
        }
        
        return activeBids;
    }

    /**
     * @dev Get tokens owned by address
     */
    function tokensOfOwner(address owner) public view returns (uint256[] memory) {
        return userTokens[owner];
    }

    /**
     * @dev Update royalty for a token (only creator)
     */
    function updateRoyalty(
        uint256 tokenId,
        address recipient,
        uint96 feeNumerator
    ) public {
        require(_exists(tokenId), "Token does not exist");
        require(tokenInfo[tokenId].creator == msg.sender, "Not the creator");
        require(feeNumerator <= maximumRoyalty, "Royalty too high");

        _setTokenRoyalty(tokenId, recipient, feeNumerator);
        emit RoyaltyUpdated(tokenId, recipient, feeNumerator);
    }

    /**
     * @dev Set marketplace fee (only owner)
     */
    function setMarketplaceFee(uint256 _feePercentage) public onlyOwner {
        require(_feePercentage <= 1000, "Fee too high"); // Max 10%
        marketplaceFeePercentage = _feePercentage;
    }

    /**
     * @dev Set marketplace fee recipient (only owner)
     */
    function setMarketplaceFeeRecipient(address _recipient) public onlyOwner {
        require(_recipient != address(0), "Invalid recipient");
        marketplaceFeeRecipient = _recipient;
    }

    /**
     * @dev Set base URI for tokens
     */
    function setBaseURI(string memory baseURI) public onlyOwner {
        baseTokenURI = baseURI;
    }

    /**
     * @dev Toggle public minting
     */
    function setPublicMintEnabled(bool enabled) public onlyOwner {
        publicMintEnabled = enabled;
    }

    /**
     * @dev Set mint price
     */
    function setMintPrice(uint256 price) public onlyOwner {
        mintPrice = price;
    }

    /**
     * @dev Get current token ID
     */
    function getCurrentTokenId() public view returns (uint256) {
        return _tokenIdCounter.current();
    }

    /**
     * @dev Get total supply
     */
    function totalSupply() public view returns (uint256) {
        return _tokenIdCounter.current();
    }

    /**
     * @dev Override _beforeTokenTransfer to check transferability
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
            require(tokenInfo[tokenId].transferable, "Token not transferable");
        }

        // Update user token tracking
        if (from != address(0) && from != to) {
            // Remove from old owner
            uint256[] storage fromTokens = userTokens[from];
            uint256 index = userTokenIndex[tokenId];
            uint256 lastTokenId = fromTokens[fromTokens.length - 1];
            
            fromTokens[index] = lastTokenId;
            userTokenIndex[lastTokenId] = index;
            fromTokens.pop();
        }

        if (to != address(0) && from != to) {
            // Add to new owner
            userTokens[to].push(tokenId);
            userTokenIndex[tokenId] = userTokens[to].length - 1;
        }
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
     * @dev Emergency withdraw (only owner)
     */
    function emergencyWithdraw() public onlyOwner {
        payable(owner()).transfer(address(this).balance);
    }

    // Override required functions
    function _burn(uint256 tokenId) internal override(ERC721, ERC721URIStorage, ERC721Royalty) {
        super._burn(tokenId);
        
        // Clean up token info
        delete tokenInfo[tokenId];
        
        // Remove from user tokens
        address owner = ownerOf(tokenId);
        uint256[] storage ownerTokens = userTokens[owner];
        uint256 index = userTokenIndex[tokenId];
        uint256 lastTokenId = ownerTokens[ownerTokens.length - 1];
        
        ownerTokens[index] = lastTokenId;
        userTokenIndex[lastTokenId] = index;
        ownerTokens.pop();
        delete userTokenIndex[tokenId];
    }

    function tokenURI(uint256 tokenId)
        public
        view
        override(ERC721, ERC721URIStorage)
        returns (string memory)
    {
        return super.tokenURI(tokenId);
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC721URIStorage, ERC721Royalty)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }

    /**
     * @dev Override _baseURI to return the base URI
     */
    function _baseURI() internal view override returns (string memory) {
        return baseTokenURI;
    }
}