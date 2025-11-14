declare module 'pdfjs-dist/build/pdf' {
  export const GlobalWorkerOptions: {
    workerSrc: string;
  };
  
  export const version: string;
  
  export function getDocument(src: string | ArrayBuffer | Uint8Array): {
    promise: Promise<PDFDocumentProxy>;
  };
  
  export interface PDFDocumentProxy {
    getPage(pageNumber: number): Promise<PDFPageProxy>;
  }
  
  export interface PDFPageProxy {
    getViewport(params: { scale: number }): Viewport;
    render(params: {
      canvasContext: CanvasRenderingContext2D;
      viewport: Viewport;
    }): RenderTask;
  }
  
  export interface Viewport {
    width: number;
    height: number;
  }
  
  export interface RenderTask {
    promise: Promise<void>;
  }
}

