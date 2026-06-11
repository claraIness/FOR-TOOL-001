# Configurar inicio de sesion con Microsoft

FORENSIA usa OpenID Connect mediante `st.login`. Las contrasenas nunca se guardan
en SQLite ni dentro del repositorio.

## 1. Instalar dependencias

```powershell
pip install -r requirements.txt
```

## 2. Registrar la aplicacion en Microsoft Entra

1. Abrir el portal de Microsoft Entra y entrar en **Registros de aplicaciones**.
2. Crear un registro llamado `FORENSIA`.
3. Elegir los tipos de cuenta que podran iniciar sesion.
4. Agregar una plataforma **Web**.
5. Registrar esta URI de redireccion local:

```text
http://localhost:8501/oauth2callback
```

6. Copiar el **Id. de aplicacion (cliente)**.
7. Crear un secreto de cliente y copiar su **valor** inmediatamente.

## 3. Crear el archivo local de secretos

Copiar `.streamlit/secrets.toml.example` como `.streamlit/secrets.toml` y
reemplazar los tres valores indicados.

La configuracion incluida usa el endpoint `consumers`, adecuado para iniciar
sesion con cuentas personales de Microsoft como Outlook o Hotmail.

El secreto de cookie debe ser largo y aleatorio. Puede generarse con:

```powershell
py -c "import secrets; print(secrets.token_urlsafe(48))"
```

El archivo `.streamlit/secrets.toml` esta ignorado por Git y no debe compartirse.

## 4. Iniciar FORENSIA

```powershell
streamlit run app.py
```

Al abrir `http://localhost:8501`, la aplicacion mostrara solamente el acceso con
Microsoft. Despues de autenticar, Microsoft regresara a FORENSIA y se mostrara
el usuario conectado junto al boton **Cerrar sesion**.

## Despliegue posterior

Al publicar la aplicacion, hay que registrar tambien la URI publica terminada en
`/oauth2callback` y actualizar `redirect_uri` en los secretos del servidor.
