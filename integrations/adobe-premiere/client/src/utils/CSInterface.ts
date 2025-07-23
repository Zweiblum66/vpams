/**
 * CSInterface - Adobe CEP JavaScript Interface
 * This is a TypeScript wrapper around Adobe's CSInterface library
 */

declare global {
  interface Window {
    __adobe_cep__: any;
    cep: any;
  }
}

export class CSInterface {
  private cepVersion: string;

  constructor() {
    this.cepVersion = this.getCurrentCEPVersion();
  }

  getCurrentCEPVersion(): string {
    const cep = window.__adobe_cep__ || window.cep;
    return cep?.getCurrentApiVersion() || '10.0.0';
  }

  getHostEnvironment() {
    const cep = window.__adobe_cep__ || window.cep;
    const hostEnvironment = JSON.parse(cep?.getHostEnvironment() || '{}');
    return {
      appName: hostEnvironment.appName || 'PPRO',
      appVersion: hostEnvironment.appVersion || '2023',
      appLocale: hostEnvironment.appLocale || 'en_US',
      appUILocale: hostEnvironment.appUILocale || 'en_US',
      appId: hostEnvironment.appId || 'PPRO',
      isAppOnline: hostEnvironment.isAppOnline !== false,
      appSkinInfo: {
        baseFontFamily: hostEnvironment.appSkinInfo?.baseFontFamily || 'Arial',
        baseFontSize: hostEnvironment.appSkinInfo?.baseFontSize || '10px',
        appBarBackgroundColor: this.toRGBA(hostEnvironment.appSkinInfo?.appBarBackgroundColor),
        panelBackgroundColor: this.toRGBA(hostEnvironment.appSkinInfo?.panelBackgroundColor),
        appBarBackgroundColorSRGB: this.toRGBA(hostEnvironment.appSkinInfo?.appBarBackgroundColorSRGB),
        panelBackgroundColorSRGB: this.toRGBA(hostEnvironment.appSkinInfo?.panelBackgroundColorSRGB),
      }
    };
  }

  private toRGBA(colorObj: any) {
    if (!colorObj) {
      return { color: { red: 50, green: 50, blue: 50 }, alpha: 1 };
    }
    return {
      color: {
        red: colorObj.color?.red || 50,
        green: colorObj.color?.green || 50,
        blue: colorObj.color?.blue || 50,
      },
      alpha: colorObj.alpha || 1,
    };
  }

  evalScript(script: string, callback?: (result: string) => void) {
    const cep = window.__adobe_cep__ || window.cep;
    if (cep?.evalScript) {
      cep.evalScript(script, callback);
    } else {
      // Fallback for development
      console.log('evalScript:', script);
      if (callback) {
        callback('{}');
      }
    }
  }

  addEventListener(type: string, listener: (event: any) => void) {
    const cep = window.__adobe_cep__ || window.cep;
    if (cep?.addEventListener) {
      cep.addEventListener(type, listener);
    } else {
      // Fallback for development
      window.addEventListener(type, listener);
    }
  }

  removeEventListener(type: string, listener: (event: any) => void) {
    const cep = window.__adobe_cep__ || window.cep;
    if (cep?.removeEventListener) {
      cep.removeEventListener(type, listener);
    } else {
      // Fallback for development
      window.removeEventListener(type, listener);
    }
  }

  dispatchEvent(event: CSXSEvent) {
    const cep = window.__adobe_cep__ || window.cep;
    if (cep?.dispatchEvent) {
      cep.dispatchEvent(event);
    } else {
      // Fallback for development
      window.dispatchEvent(new CustomEvent(event.type, { detail: event.data }));
    }
  }

  openURLInDefaultBrowser(url: string) {
    const cep = window.__adobe_cep__ || window.cep;
    if (cep?.util?.openURLInDefaultBrowser) {
      cep.util.openURLInDefaultBrowser(url);
    } else {
      window.open(url, '_blank');
    }
  }

  getSystemPath(pathType: SystemPath): string {
    const cep = window.__adobe_cep__ || window.cep;
    if (cep?.getSystemPath) {
      return cep.getSystemPath(pathType);
    } else {
      // Fallback paths for development
      switch (pathType) {
        case SystemPath.USER_DATA:
          return '/tmp/userData';
        case SystemPath.COMMON_FILES:
          return '/tmp/commonFiles';
        case SystemPath.MY_DOCUMENTS:
          return '/tmp/documents';
        case SystemPath.APPLICATION:
          return '/tmp/application';
        case SystemPath.EXTENSION:
          return '/tmp/extension';
        case SystemPath.HOST_APPLICATION:
          return '/tmp/hostApplication';
        default:
          return '/tmp';
      }
    }
  }

  closeExtension() {
    const cep = window.__adobe_cep__ || window.cep;
    if (cep?.closeExtension) {
      cep.closeExtension();
    } else {
      console.log('Extension would close');
    }
  }

  requestOpenExtension(extensionId: string, params?: string) {
    const cep = window.__adobe_cep__ || window.cep;
    if (cep?.requestOpenExtension) {
      cep.requestOpenExtension(extensionId, params);
    } else {
      console.log('Would open extension:', extensionId);
    }
  }
}

export class CSXSEvent {
  type: string;
  scope: string;
  appId: string;
  extensionId: string;
  data: any;

  constructor() {
    this.type = '';
    this.scope = 'APPLICATION';
    this.appId = '';
    this.extensionId = '';
    this.data = '';
  }

  dispatch() {
    const csInterface = new CSInterface();
    csInterface.dispatchEvent(this);
  }
}

export enum SystemPath {
  USER_DATA = 'userData',
  COMMON_FILES = 'commonFiles',
  MY_DOCUMENTS = 'myDocuments',
  APPLICATION = 'application',
  EXTENSION = 'extension',
  HOST_APPLICATION = 'hostApplication',
}