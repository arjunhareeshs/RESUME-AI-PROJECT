import React, { useEffect, useRef } from 'react';
import * as pdfjsLib from 'pdfjs-dist/build/pdf';
// This worker is crucial
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;

interface Props {
  fileUrl: string;
}

export const ResumePreview: React.FC<Props> = ({ fileUrl }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!fileUrl) return;

    const renderPdf = async () => {
      try {
        const loadingTask = pdfjsLib.getDocument(fileUrl);
        const pdf = await loadingTask.promise;
        const page = await pdf.getPage(1); // Render first page
        
        const viewport = page.getViewport({ scale: 1.5 });
        const canvas = canvasRef.current;
        if (!canvas) return;

        const context = canvas.getContext('2d');
        if (!context) return;
        
        canvas.height = viewport.height;
        canvas.width = viewport.width;

        page.render({ canvasContext: context, viewport: viewport });
      } catch (error) {
        console.error('Error rendering PDF:', error);
      }
    };
    
    renderPdf();
  }, [fileUrl]);

  return (
    <div className="p-4 bg-gray-200 flex justify-center">
      <canvas ref={canvasRef} className="shadow-lg" />
    </div>
  );
};