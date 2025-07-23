// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/draft-EIP712.sol";

/**
 * @title ProvenanceTracker
 * @dev Comprehensive provenance tracking for digital media assets
 */
contract ProvenanceTracker is Ownable, Pausable, ReentrancyGuard, EIP712 {
    using Counters for Counters.Counter;
    using ECDSA for bytes32;

    Counters.Counter private _assetIdCounter;
    Counters.Counter private _eventIdCounter;

    // Events
    event AssetRegistered(
        uint256 indexed assetId,
        bytes32 indexed assetHash,
        address indexed registrar,
        string metadata
    );
    
    event ProvenanceEventAdded(
        uint256 indexed eventId,
        uint256 indexed assetId,
        address indexed actor,
        string eventType,
        bytes32 dataHash
    );
    
    event OwnershipTransferred(
        uint256 indexed assetId,
        address indexed from,
        address indexed to,
        uint256 timestamp
    );
    
    event AssetModified(
        uint256 indexed assetId,
        bytes32 indexed newHash,
        address indexed modifier,
        string modificationType
    );
    
    event LicenseGranted(
        uint256 indexed assetId,
        address indexed licensee,
        string licenseType,
        uint256 expiresAt
    );
    
    event VerificationAdded(
        uint256 indexed assetId,
        address indexed verifier,
        string verificationType,
        bool verified
    );

    // Structs
    struct Asset {
        uint256 id;
        bytes32 contentHash;
        address creator;
        address currentOwner;
        uint256 createdAt;
        uint256 lastModified;
        string title;
        string description;
        string assetType; // image, video, audio, document, etc.
        AssetStatus status;
        bool verified;
        uint256 eventCount;
    }

    struct ProvenanceEvent {
        uint256 id;
        uint256 assetId;
        address actor;
        uint256 timestamp;
        string eventType; // created, modified, transferred, licensed, verified, etc.
        bytes32 dataHash;
        string metadata;
        bytes signature;
        bool verified;
    }

    struct License {
        uint256 assetId;
        address licensor;
        address licensee;
        string licenseType;
        string terms;
        uint256 grantedAt;
        uint256 expiresAt;
        bool active;
        bytes32 termsHash;
    }

    struct Verification {
        uint256 assetId;
        address verifier;
        string verificationType; // authenticity, ownership, quality, compliance
        bool verified;
        uint256 verifiedAt;
        string evidence;
        bytes32 evidenceHash;
    }

    struct Attribution {
        uint256 assetId;
        address contributor;
        string contributionType; // creator, editor, photographer, etc.
        uint256 percentage; // contribution percentage (basis points)
        uint256 addedAt;
        bool active;
    }

    enum AssetStatus {
        ACTIVE,
        ARCHIVED,
        DISPUTED,
        DELETED
    }

    // Storage
    mapping(uint256 => Asset) public assets;
    mapping(bytes32 => uint256) public hashToAssetId;
    mapping(uint256 => ProvenanceEvent[]) public assetEvents;
    mapping(uint256 => License[]) public assetLicenses;
    mapping(uint256 => Verification[]) public assetVerifications;
    mapping(uint256 => Attribution[]) public assetAttributions;
    mapping(address => uint256[]) public userAssets;
    mapping(address => bool) public authorizedVerifiers;
    
    // Chain of custody tracking
    mapping(uint256 => address[]) public custodyChain;
    mapping(uint256 => mapping(address => uint256)) public custodyTimestamps;
    
    // Batch operations
    mapping(bytes32 => uint256[]) public batchAssets;
    mapping(uint256 => bytes32) public assetToBatch;

    // EIP-712 Type Hashes
    bytes32 private constant PROVENANCE_EVENT_TYPEHASH = 
        keccak256("ProvenanceEvent(uint256 assetId,address actor,uint256 timestamp,string eventType,bytes32 dataHash,string metadata)");

    modifier onlyAssetOwner(uint256 assetId) {
        require(_exists(assetId), "Asset does not exist");
        require(assets[assetId].currentOwner == msg.sender, "Not asset owner");
        _;
    }

    modifier onlyAuthorizedVerifier() {
        require(authorizedVerifiers[msg.sender] || msg.sender == owner(), "Not authorized verifier");
        _;
    }

    constructor() EIP712("ProvenanceTracker", "1") {
        authorizedVerifiers[msg.sender] = true;
    }

    /**
     * @dev Register a new asset with initial provenance
     */
    function registerAsset(
        bytes32 contentHash,
        string memory title,
        string memory description,
        string memory assetType,
        string memory metadata
    ) external whenNotPaused returns (uint256) {
        require(contentHash != bytes32(0), "Invalid content hash");
        require(hashToAssetId[contentHash] == 0, "Asset already registered");
        require(bytes(title).length > 0, "Title required");

        uint256 assetId = _assetIdCounter.current();
        _assetIdCounter.increment();

        assets[assetId] = Asset({
            id: assetId,
            contentHash: contentHash,
            creator: msg.sender,
            currentOwner: msg.sender,
            createdAt: block.timestamp,
            lastModified: block.timestamp,
            title: title,
            description: description,
            assetType: assetType,
            status: AssetStatus.ACTIVE,
            verified: false,
            eventCount: 0
        });

        hashToAssetId[contentHash] = assetId;
        userAssets[msg.sender].push(assetId);
        custodyChain[assetId].push(msg.sender);
        custodyTimestamps[assetId][msg.sender] = block.timestamp;

        // Add initial creation event
        _addProvenanceEvent(
            assetId,
            msg.sender,
            "created",
            contentHash,
            metadata,
            ""
        );

        emit AssetRegistered(assetId, contentHash, msg.sender, metadata);
        return assetId;
    }

    /**
     * @dev Add a provenance event to an asset
     */
    function addProvenanceEvent(
        uint256 assetId,
        string memory eventType,
        bytes32 dataHash,
        string memory metadata,
        bytes memory signature
    ) external whenNotPaused {
        require(_exists(assetId), "Asset does not exist");
        require(
            assets[assetId].currentOwner == msg.sender || 
            authorizedVerifiers[msg.sender] ||
            msg.sender == owner(),
            "Not authorized to add event"
        );

        _addProvenanceEvent(assetId, msg.sender, eventType, dataHash, metadata, signature);
    }

    /**
     * @dev Internal function to add provenance event
     */
    function _addProvenanceEvent(
        uint256 assetId,
        address actor,
        string memory eventType,
        bytes32 dataHash,
        string memory metadata,
        bytes memory signature
    ) internal {
        uint256 eventId = _eventIdCounter.current();
        _eventIdCounter.increment();

        // Verify signature if provided
        bool signatureVerified = false;
        if (signature.length > 0) {
            bytes32 structHash = keccak256(abi.encode(
                PROVENANCE_EVENT_TYPEHASH,
                assetId,
                actor,
                block.timestamp,
                keccak256(bytes(eventType)),
                dataHash,
                keccak256(bytes(metadata))
            ));
            bytes32 hash = _hashTypedDataV4(structHash);
            address signer = hash.recover(signature);
            signatureVerified = (signer == actor);
        }

        ProvenanceEvent memory newEvent = ProvenanceEvent({
            id: eventId,
            assetId: assetId,
            actor: actor,
            timestamp: block.timestamp,
            eventType: eventType,
            dataHash: dataHash,
            metadata: metadata,
            signature: signature,
            verified: signatureVerified
        });

        assetEvents[assetId].push(newEvent);
        assets[assetId].eventCount++;
        assets[assetId].lastModified = block.timestamp;

        emit ProvenanceEventAdded(eventId, assetId, actor, eventType, dataHash);
    }

    /**
     * @dev Transfer ownership of an asset
     */
    function transferOwnership(
        uint256 assetId,
        address newOwner
    ) external onlyAssetOwner(assetId) whenNotPaused {
        require(newOwner != address(0), "Invalid new owner");
        require(newOwner != assets[assetId].currentOwner, "Already owner");

        address previousOwner = assets[assetId].currentOwner;
        assets[assetId].currentOwner = newOwner;

        // Update user assets
        userAssets[newOwner].push(assetId);
        
        // Update custody chain
        custodyChain[assetId].push(newOwner);
        custodyTimestamps[assetId][newOwner] = block.timestamp;

        // Add provenance event
        _addProvenanceEvent(
            assetId,
            msg.sender,
            "ownership_transferred",
            keccak256(abi.encodePacked(previousOwner, newOwner)),
            string(abi.encodePacked("Transfer from ", addressToString(previousOwner), " to ", addressToString(newOwner))),
            ""
        );

        emit OwnershipTransferred(assetId, previousOwner, newOwner, block.timestamp);
    }

    /**
     * @dev Update asset content (creates new version)
     */
    function updateAssetContent(
        uint256 assetId,
        bytes32 newContentHash,
        string memory modificationType,
        string memory metadata
    ) external onlyAssetOwner(assetId) whenNotPaused {
        require(newContentHash != bytes32(0), "Invalid content hash");
        require(newContentHash != assets[assetId].contentHash, "Hash unchanged");
        
        bytes32 previousHash = assets[assetId].contentHash;
        
        // Update hash mapping
        delete hashToAssetId[previousHash];
        hashToAssetId[newContentHash] = assetId;
        
        assets[assetId].contentHash = newContentHash;
        assets[assetId].lastModified = block.timestamp;

        // Add provenance event
        _addProvenanceEvent(
            assetId,
            msg.sender,
            "modified",
            newContentHash,
            metadata,
            ""
        );

        emit AssetModified(assetId, newContentHash, msg.sender, modificationType);
    }

    /**
     * @dev Grant a license for an asset
     */
    function grantLicense(
        uint256 assetId,
        address licensee,
        string memory licenseType,
        string memory terms,
        uint256 duration
    ) external onlyAssetOwner(assetId) whenNotPaused {
        require(licensee != address(0), "Invalid licensee");
        require(bytes(licenseType).length > 0, "License type required");

        uint256 expiresAt = duration > 0 ? block.timestamp + duration : 0;
        bytes32 termsHash = keccak256(bytes(terms));

        License memory newLicense = License({
            assetId: assetId,
            licensor: msg.sender,
            licensee: licensee,
            licenseType: licenseType,
            terms: terms,
            grantedAt: block.timestamp,
            expiresAt: expiresAt,
            active: true,
            termsHash: termsHash
        });

        assetLicenses[assetId].push(newLicense);

        // Add provenance event
        _addProvenanceEvent(
            assetId,
            msg.sender,
            "license_granted",
            termsHash,
            string(abi.encodePacked("License granted to ", addressToString(licensee), " - ", licenseType)),
            ""
        );

        emit LicenseGranted(assetId, licensee, licenseType, expiresAt);
    }

    /**
     * @dev Add verification to an asset
     */
    function addVerification(
        uint256 assetId,
        string memory verificationType,
        bool verified,
        string memory evidence
    ) external onlyAuthorizedVerifier whenNotPaused {
        require(_exists(assetId), "Asset does not exist");
        require(bytes(verificationType).length > 0, "Verification type required");

        bytes32 evidenceHash = keccak256(bytes(evidence));

        Verification memory newVerification = Verification({
            assetId: assetId,
            verifier: msg.sender,
            verificationType: verificationType,
            verified: verified,
            verifiedAt: block.timestamp,
            evidence: evidence,
            evidenceHash: evidenceHash
        });

        assetVerifications[assetId].push(newVerification);

        // Update asset verification status if authenticity verified
        if (keccak256(bytes(verificationType)) == keccak256(bytes("authenticity")) && verified) {
            assets[assetId].verified = true;
        }

        // Add provenance event
        _addProvenanceEvent(
            assetId,
            msg.sender,
            "verification_added",
            evidenceHash,
            string(abi.encodePacked("Verification: ", verificationType, " - ", verified ? "VERIFIED" : "FAILED")),
            ""
        );

        emit VerificationAdded(assetId, msg.sender, verificationType, verified);
    }

    /**
     * @dev Add attribution to an asset
     */
    function addAttribution(
        uint256 assetId,
        address contributor,
        string memory contributionType,
        uint256 percentage
    ) external onlyAssetOwner(assetId) whenNotPaused {
        require(contributor != address(0), "Invalid contributor");
        require(bytes(contributionType).length > 0, "Contribution type required");
        require(percentage <= 10000, "Percentage cannot exceed 100%");

        Attribution memory newAttribution = Attribution({
            assetId: assetId,
            contributor: contributor,
            contributionType: contributionType,
            percentage: percentage,
            addedAt: block.timestamp,
            active: true
        });

        assetAttributions[assetId].push(newAttribution);

        // Add provenance event
        _addProvenanceEvent(
            assetId,
            msg.sender,
            "attribution_added",
            keccak256(abi.encodePacked(contributor, contributionType, percentage)),
            string(abi.encodePacked("Attribution: ", addressToString(contributor), " - ", contributionType)),
            ""
        );
    }

    /**
     * @dev Register batch of assets
     */
    function registerAssetBatch(
        bytes32[] memory contentHashes,
        string[] memory titles,
        string[] memory descriptions,
        string[] memory assetTypes,
        string memory batchMetadata
    ) external whenNotPaused returns (uint256[] memory) {
        require(contentHashes.length == titles.length, "Array length mismatch");
        require(contentHashes.length == descriptions.length, "Array length mismatch");
        require(contentHashes.length == assetTypes.length, "Array length mismatch");
        require(contentHashes.length > 0, "Empty batch");

        bytes32 batchId = keccak256(abi.encodePacked(msg.sender, block.timestamp, batchMetadata));
        uint256[] memory assetIds = new uint256[](contentHashes.length);

        for (uint256 i = 0; i < contentHashes.length; i++) {
            uint256 assetId = registerAsset(
                contentHashes[i],
                titles[i],
                descriptions[i],
                assetTypes[i],
                batchMetadata
            );
            assetIds[i] = assetId;
            batchAssets[batchId].push(assetId);
            assetToBatch[assetId] = batchId;
        }

        return assetIds;
    }

    /**
     * @dev Get asset provenance history
     */
    function getAssetHistory(uint256 assetId) 
        external 
        view 
        returns (ProvenanceEvent[] memory) 
    {
        require(_exists(assetId), "Asset does not exist");
        return assetEvents[assetId];
    }

    /**
     * @dev Get asset licenses
     */
    function getAssetLicenses(uint256 assetId) 
        external 
        view 
        returns (License[] memory) 
    {
        require(_exists(assetId), "Asset does not exist");
        return assetLicenses[assetId];
    }

    /**
     * @dev Get asset verifications
     */
    function getAssetVerifications(uint256 assetId) 
        external 
        view 
        returns (Verification[] memory) 
    {
        require(_exists(assetId), "Asset does not exist");
        return assetVerifications[assetId];
    }

    /**
     * @dev Get asset attributions
     */
    function getAssetAttributions(uint256 assetId) 
        external 
        view 
        returns (Attribution[] memory) 
    {
        require(_exists(assetId), "Asset does not exist");
        return assetAttributions[assetId];
    }

    /**
     * @dev Get custody chain
     */
    function getCustodyChain(uint256 assetId) 
        external 
        view 
        returns (address[] memory) 
    {
        require(_exists(assetId), "Asset does not exist");
        return custodyChain[assetId];
    }

    /**
     * @dev Get user assets
     */
    function getUserAssets(address user) external view returns (uint256[] memory) {
        return userAssets[user];
    }

    /**
     * @dev Get batch assets
     */
    function getBatchAssets(bytes32 batchId) external view returns (uint256[] memory) {
        return batchAssets[batchId];
    }

    /**
     * @dev Check if asset exists
     */
    function _exists(uint256 assetId) internal view returns (bool) {
        return assetId < _assetIdCounter.current() && assets[assetId].status != AssetStatus.DELETED;
    }

    /**
     * @dev Verify asset authenticity
     */
    function verifyAssetAuthenticity(uint256 assetId, bytes32 expectedHash) 
        external 
        view 
        returns (bool) 
    {
        require(_exists(assetId), "Asset does not exist");
        return assets[assetId].contentHash == expectedHash && assets[assetId].verified;
    }

    /**
     * @dev Add authorized verifier
     */
    function addAuthorizedVerifier(address verifier) external onlyOwner {
        require(verifier != address(0), "Invalid verifier address");
        authorizedVerifiers[verifier] = true;
    }

    /**
     * @dev Remove authorized verifier
     */
    function removeAuthorizedVerifier(address verifier) external onlyOwner {
        authorizedVerifiers[verifier] = false;
    }

    /**
     * @dev Update asset status
     */
    function updateAssetStatus(uint256 assetId, AssetStatus newStatus) 
        external 
        onlyAssetOwner(assetId) 
        whenNotPaused 
    {
        assets[assetId].status = newStatus;
        
        _addProvenanceEvent(
            assetId,
            msg.sender,
            "status_updated",
            keccak256(abi.encodePacked(uint8(newStatus))),
            string(abi.encodePacked("Status updated to: ", uint8(newStatus))),
            ""
        );
    }

    /**
     * @dev Get current asset count
     */
    function getCurrentAssetCount() external view returns (uint256) {
        return _assetIdCounter.current();
    }

    /**
     * @dev Get current event count
     */
    function getCurrentEventCount() external view returns (uint256) {
        return _eventIdCounter.current();
    }

    /**
     * @dev Convert address to string
     */
    function addressToString(address addr) internal pure returns (string memory) {
        bytes32 value = bytes32(uint256(uint160(addr)));
        bytes memory alphabet = "0123456789abcdef";
        bytes memory str = new bytes(42);
        str[0] = '0';
        str[1] = 'x';
        for (uint256 i = 0; i < 20; i++) {
            str[2+i*2] = alphabet[uint8(value[i + 12] >> 4)];
            str[3+i*2] = alphabet[uint8(value[i + 12] & 0x0f)];
        }
        return string(str);
    }

    /**
     * @dev Pause contract
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @dev Unpause contract
     */
    function unpause() external onlyOwner {
        _unpause();
    }
}