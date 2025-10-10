// Type definitions for Google Picker API and Google API Client
// These types are needed for our custom Google Drive Picker implementation

declare global {
  interface Window {
    google?: typeof google;
    gapi?: {
      load: (api: string, callback: () => void) => void;
    };
  }
}

// The 'google' namespace is used as a type, not as a variable
// eslint-disable-next-line @typescript-eslint/no-unused-vars
declare namespace google {
  namespace picker {
    enum ViewId {
      FOLDERS = 'folders',
      DOCS = 'docs',
    }

    enum Action {
      PICKED = 'picked',
      CANCEL = 'cancel',
    }

    interface Document {
      id: string;
      name: string;
      mimeType: string;
      url?: string;
    }

    interface ResponseObject {
      action: string;
      docs?: Document[];
    }

    class DocsView {
      constructor(viewId: ViewId);
      setSelectFolderEnabled(enabled: boolean): DocsView;
      setIncludeFolders(include: boolean): DocsView;
    }

    class PickerBuilder {
      addView(view: DocsView): PickerBuilder;
      setOAuthToken(token: string): PickerBuilder;
      setDeveloperKey(key: string): PickerBuilder;
      setCallback(callback: (data: ResponseObject) => void): PickerBuilder;
      build(): Picker;
    }

    interface Picker {
      setVisible(visible: boolean): void;
    }
  }
}

export {};
