import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import Icon from './Icon';
import { UploadCloud } from 'lucide-react';

interface FileUploadProps {
  onFileUpload: (files: File[]) => void;
}

export default function FileUpload({ onFileUpload }: FileUploadProps) {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    onFileUpload(acceptedFiles);
  }, [onFileUpload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, accept: { 'application/pdf': ['.pdf'] }, multiple: true });

  return (
    <div
      {...getRootProps()}
      className={`ring-focus rounded-xl p-10 text-center cursor-pointer transition-all duration-300 ${
        isDragActive ? 'bg-blue-50 border-2 border-dashed border-blue-400 scale-[1.01]' : 'bg-gray-50 border border-dashed border-gray-300 hover:shadow-md'
      }`}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-2">
        <div className="inline-flex p-3 rounded-full bg-white shadow-sm">
          <Icon icon={UploadCloud} color="primary" />
        </div>
        {isDragActive ? (
          <p className="text-blue-600 font-medium">Drop the files here…</p>
        ) : (
          <>
            <p className="text-gray-700 font-medium">Drag and drop PDF files here</p>
            <p className="text-gray-500 text-sm">or click to select files</p>
          </>
        )}
      </div>
    </div>
  );
}