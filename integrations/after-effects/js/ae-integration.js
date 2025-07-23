/**
 * After Effects Integration
 * Handles communication between CEP panel and After Effects ExtendScript
 */

class AEIntegration {
    constructor() {
        this.csInterface = new CSInterface();
        this.extensionId = this.csInterface.getExtensionID();
        this.hostEnvironment = this.csInterface.getHostEnvironment();
        this.isConnected = false;
        
        this.initialize();
    }

    /**
     * Initialize After Effects integration
     */
    async initialize() {
        try {
            // Load host script
            await this.loadHostScript();
            
            // Test connection
            await this.testConnection();
            
            // Setup event listeners
            this.setupEventListeners();
            
            console.log('After Effects integration initialized');
        } catch (error) {
            console.error('Failed to initialize AE integration:', error);
        }
    }

    /**
     * Load ExtendScript host script
     */
    loadHostScript() {
        return new Promise((resolve, reject) => {
            const scriptPath = this.csInterface.getSystemPath(SystemPath.EXTENSION) + '/jsx/mams-ae-host.jsx';
            this.csInterface.evalScript(`$.evalFile("${scriptPath}")`, (result) => {
                if (result === 'EvalScript error.') {
                    reject(new Error('Failed to load host script'));
                } else {
                    resolve(result);
                }
            });
        });
    }

    /**
     * Test connection to After Effects
     */
    testConnection() {
        return new Promise((resolve, reject) => {
            this.evalScript('MAMSAEIntegration.getApplicationInfo()', (result) => {
                try {
                    const info = JSON.parse(result);
                    this.isConnected = true;
                    resolve(info);
                } catch (error) {
                    this.isConnected = false;
                    reject(error);
                }
            });
        });
    }

    /**
     * Setup event listeners for After Effects events
     */
    setupEventListeners() {
        // Listen for application events
        this.csInterface.addEventListener('com.adobe.csxs.events.ApplicationBeforeQuit', () => {
            this.onApplicationQuit();
        });

        // Listen for theme changes
        this.csInterface.addEventListener('com.adobe.csxs.events.ThemeColorChanged', (event) => {
            this.onThemeChanged(event);
        });
    }

    /**
     * Execute ExtendScript in After Effects
     */
    evalScript(script, callback) {
        this.csInterface.evalScript(script, callback || (() => {}));
    }

    /**
     * Import asset as footage
     */
    async importAsFootage(assetData, filePath, metadata = {}) {
        return new Promise((resolve, reject) => {
            const script = `
                MAMSAEIntegration.importAsFootage(
                    "${filePath}",
                    "${assetData.name}",
                    ${JSON.stringify(metadata)}
                )
            `;

            this.evalScript(script, (result) => {
                try {
                    const response = JSON.parse(result);
                    if (response.success) {
                        resolve(response);
                    } else {
                        reject(new Error(response.error));
                    }
                } catch (error) {
                    reject(error);
                }
            });
        });
    }

    /**
     * Import asset as composition
     */
    async importAsComposition(assetData, filePath, metadata = {}, compSettings = {}) {
        return new Promise((resolve, reject) => {
            const script = `
                MAMSAEIntegration.importAsComposition(
                    "${filePath}",
                    "${assetData.name}",
                    ${JSON.stringify(metadata)},
                    ${JSON.stringify(compSettings)}
                )
            `;

            this.evalScript(script, (result) => {
                try {
                    const response = JSON.parse(result);
                    if (response.success) {
                        resolve(response);
                    } else {
                        reject(new Error(response.error));
                    }
                } catch (error) {
                    reject(error);
                }
            });
        });
    }

    /**
     * Import asset as precomposition
     */
    async importAsPrecomp(assetData, filePath, metadata = {}) {
        return new Promise((resolve, reject) => {
            const script = `
                MAMSAEIntegration.importAsPrecomp(
                    "${filePath}",
                    "${assetData.name}",
                    ${JSON.stringify(metadata)}
                )
            `;

            this.evalScript(script, (result) => {
                try {
                    const response = JSON.parse(result);
                    if (response.success) {
                        resolve(response);
                    } else {
                        reject(new Error(response.error));
                    }
                } catch (error) {
                    reject(error);
                }
            });
        });
    }

    /**
     * Apply motion graphics template
     */
    async applyTemplate(templateData, templatePath, targetCompId, parameters = {}) {
        return new Promise((resolve, reject) => {
            const script = `
                MAMSAEIntegration.applyTemplate(
                    "${templatePath}",
                    ${targetCompId},
                    ${JSON.stringify(parameters)}
                )
            `;

            this.evalScript(script, (result) => {
                try {
                    const response = JSON.parse(result);
                    if (response.success) {
                        resolve(response);
                    } else {
                        reject(new Error(response.error));
                    }
                } catch (error) {
                    reject(error);
                }
            });
        });
    }

    /**
     * Get current composition info
     */
    async getCurrentComposition() {
        return new Promise((resolve, reject) => {
            this.evalScript('MAMSAEIntegration.getCurrentComposition()', (result) => {
                try {
                    const response = JSON.parse(result);
                    if (response.success) {
                        resolve(response);
                    } else {
                        reject(new Error(response.error));
                    }
                } catch (error) {
                    reject(error);
                }
            });
        });
    }

    /**
     * Add composition to render queue
     */
    async addToRenderQueue(compId, outputSettings) {
        return new Promise((resolve, reject) => {
            const script = `
                MAMSAEIntegration.addToRenderQueue(
                    ${compId},
                    ${JSON.stringify(outputSettings)}
                )
            `;

            this.evalScript(script, (result) => {
                try {
                    const response = JSON.parse(result);
                    if (response.success) {
                        resolve(response);
                    } else {
                        reject(new Error(response.error));
                    }
                } catch (error) {
                    reject(error);
                }
            });
        });
    }

    /**
     * Start render queue
     */
    async startRenderQueue() {
        return new Promise((resolve, reject) => {
            this.evalScript('MAMSAEIntegration.startRenderQueue()', (result) => {
                try {
                    const response = JSON.parse(result);
                    if (response.success) {
                        resolve(response);
                    } else {
                        reject(new Error(response.error));
                    }
                } catch (error) {
                    reject(error);
                }
            });
        });
    }

    /**
     * Export project structure
     */
    async exportProjectStructure() {
        return new Promise((resolve, reject) => {
            this.evalScript('MAMSAEIntegration.exportProjectStructure()', (result) => {
                try {
                    const response = JSON.parse(result);
                    if (response.success) {
                        resolve(response.projectData);
                    } else {
                        reject(new Error(response.error));
                    }
                } catch (error) {
                    reject(error);
                }
            });
        });
    }

    /**
     * Update import settings
     */
    async updateImportSettings(settings) {
        return new Promise((resolve, reject) => {
            const script = `
                MAMSAEIntegration.updateImportSettings(${JSON.stringify(settings)})
            `;

            this.evalScript(script, (result) => {
                try {
                    const response = JSON.parse(result);
                    if (response.success) {
                        resolve(response.settings);
                    } else {
                        reject(new Error(response.error));
                    }
                } catch (error) {
                    reject(error);
                }
            });
        });
    }

    /**
     * Show alert in After Effects
     */
    async showAlert(message, title = 'MAMS') {
        return new Promise((resolve) => {
            const script = `
                MAMSAEIntegration.showAlert("${message}", "${title}")
            `;

            this.evalScript(script, () => {
                resolve();
            });
        });
    }

    /**
     * Download asset to temporary location
     */
    async downloadAssetToTemp(downloadUrl, filename) {
        try {
            const response = await fetch(downloadUrl);
            if (!response.ok) {
                throw new Error(`Download failed: ${response.statusText}`);
            }

            const blob = await response.blob();
            
            // Create temporary file path
            const tempDir = this.csInterface.getSystemPath(SystemPath.USER_DATA) + '/MAMS/temp/';
            const tempPath = tempDir + filename;

            // Note: In a real CEP extension, you would use Node.js filesystem APIs
            // This is a simplified implementation
            return tempPath;
        } catch (error) {
            console.error('Download failed:', error);
            throw error;
        }
    }

    /**
     * Get After Effects application info
     */
    async getApplicationInfo() {
        return new Promise((resolve, reject) => {
            this.evalScript('MAMSAEIntegration.getApplicationInfo()', (result) => {
                try {
                    const info = JSON.parse(result);
                    resolve(info);
                } catch (error) {
                    reject(error);
                }
            });
        });
    }

    /**
     * Handle application quit event
     */
    onApplicationQuit() {
        console.log('After Effects is quitting');
        // Cleanup if needed
    }

    /**
     * Handle theme change event
     */
    onThemeChanged(event) {
        console.log('Theme changed:', event);
        // Update panel styling if needed
        this.updateTheme(event.data);
    }

    /**
     * Update panel theme
     */
    updateTheme(themeData) {
        try {
            const skinInfo = JSON.parse(themeData.skinInfo);
            const panelBgColor = skinInfo.panelBackgroundColor;
            
            // Update CSS custom properties
            document.documentElement.style.setProperty('--ae-bg-color', 
                `rgb(${panelBgColor.color.red}, ${panelBgColor.color.green}, ${panelBgColor.color.blue})`);
            
        } catch (error) {
            console.warn('Failed to update theme:', error);
        }
    }

    /**
     * Get host capabilities
     */
    getHostCapabilities() {
        return {
            hostName: this.hostEnvironment.appName,
            hostVersion: this.hostEnvironment.appVersion,
            apiVersion: this.hostEnvironment.appAPIVersion,
            isConnected: this.isConnected,
            supportedFeatures: [
                'footageImport',
                'compositionImport',
                'precompImport',
                'templateApplication',
                'renderQueue',
                'projectExport'
            ]
        };
    }

    /**
     * Validate file path for After Effects
     */
    validateFilePath(filePath) {
        // Check if file extension is supported by After Effects
        const supportedExtensions = [
            '.mov', '.mp4', '.avi', '.mkv', '.mxf',
            '.wav', '.aiff', '.mp3', '.m4a',
            '.jpg', '.jpeg', '.png', '.tiff', '.tga', '.exr', '.dpx',
            '.psd', '.ai', '.eps',
            '.aep' // After Effects project
        ];

        const extension = filePath.toLowerCase().substring(filePath.lastIndexOf('.'));
        return supportedExtensions.includes(extension);
    }

    /**
     * Get connection status
     */
    getConnectionStatus() {
        return {
            connected: this.isConnected,
            hostInfo: this.hostEnvironment,
            extensionId: this.extensionId
        };
    }

    /**
     * Refresh connection
     */
    async refreshConnection() {
        try {
            await this.testConnection();
            return this.isConnected;
        } catch (error) {
            this.isConnected = false;
            return false;
        }
    }
}

// Export for use in the main application
window.AEIntegration = AEIntegration;