import React from 'react';
import RequestUserFiles from './RequestUserFiles';
import GenericStep from './GenericStep';

const StepRenderer = ({ stepData, status, userFiles, onFileChange }) => {
    if (!stepData) return null;

    // Si el paso es RequestUserFiles, mostramos SIEMPRE el componente interactivo
    // Esto permite subir archivos antes de ejecutar (estado 'idle') o cuando se pida ('waiting_input')
    if (stepData.step === 'RequestUserFiles') {
        return (
            <RequestUserFiles
                stepParams={stepData.params}
                files={userFiles}
                onFileChange={onFileChange}
            />
        );
    }

    // Default view
    return <GenericStep stepData={stepData} status={status} />;
};

export default StepRenderer;
