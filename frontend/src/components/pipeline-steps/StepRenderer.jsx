import React from 'react';
import RequestUserFiles from './RequestUserFiles';
import EnrichWithUserInput from './EnrichWithUserInput';
import GenericStep from './GenericStep';

const StepRenderer = ({ stepData, status, userFiles, onFileChange, inputDetails, onSubmitInput }) => {
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

    // Si el paso es EnrichWithUserInput y estamos esperando input
    if (stepData.step === 'EnrichWithUserInput' && status === 'waiting_input' && inputDetails) {
        return (
            <EnrichWithUserInput
                inputDetails={inputDetails}
                onSubmit={onSubmitInput}
                status={status}
            />
        );
    }

    // Default view
    return <GenericStep stepData={stepData} status={status} />;
};

export default StepRenderer;
