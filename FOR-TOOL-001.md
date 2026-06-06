FOR-TOOL-001

## Generador de Cadena de Custodia Digital

Durante una investigación forense es necesario registrar
la evidencia digital de manera ordenada y mantener
la integridad de los elementos analizados.

Esta herramienta permite registrar una evidencia,
calcular su hash SHA256 y generar un informe básico
de cadena de custodia.

## ¿A quièn va dirigido?

- Estudiantes de informática forense.
- Analistas forenses junior.
- Personal judicial.
- Personal policial especializado.

## Informaciòn necesaria del usuario

Número de evidencia

Descripción

Responsable

Archivo digital

Fecha y hora de registro

## ¿Què genera la herramienta?

## ENTRADA

Número de evidencia
Descripción
Responsable
Archivo

## PROCESO

Lectura del archivo
Cálculo SHA256

## SALIDA

Hash SHA256 (algoritmo principal)
Registro de evidencia
Informe PDF

## Flujo de trabajo

Usuario

↓
Carga archivo

↓
Completa formulario

↓
Calcula hash

↓
Genera informe

↓
Descarga PDF

## Versiòn mìnima viable (MVP)

MVP 1.0

✓ Número de evidencia

✓ Descripción

✓ Responsable

✓ Selección de archivo

✓ Cálculo SHA256

✗ PDF

✗ Base de datos

✗ Historial

✗ Firma digital