#!/bin/bash

echo "Iniciando Backend y Frontend..."

# Asegurarse de que el comando conda activate funcione en el script
eval "$(conda shell.bash hook)"

# Iniciar el backend
echo "Iniciando backend (entorno rgenerator)..."
conda activate rgenerator
python backend/api.py &
BACKEND_PID=$!

# Iniciar el frontend
echo "Iniciando frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo "Ambos servicios están corriendo. Presiona Ctrl+C para detenerlos."

# Atrapar Ctrl+C para detener ambos procesos al salir
trap "echo 'Deteniendo servicios...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" SIGINT SIGTERM

# Mantener el script en ejecución
wait
