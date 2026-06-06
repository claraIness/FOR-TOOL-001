console.log("FORENSIA ONLINE");

const botonHash = document.getElementById("btnHash");
const botonPDF = document.getElementById("btnPDF");
const estado = document.getElementById("estado");
const registro = document.getElementById("registro");
const resultadoHash = document.getElementById("resultadoHash");

botonHash.addEventListener("click", async function () {
    const evidencia = document.getElementById("evidencia").value.trim();
    const responsable = document.getElementById("responsable").value.trim();
    const ubicacion = document.getElementById("ubicacion").value.trim();
    const estadoCustodia = document.getElementById("estadoCustodia").value.trim();
    const fechaRecepcion = document.getElementById("fechaRecepcion").value;
    const descripcion = document.getElementById("descripcion").value.trim();
    const archivo = document.getElementById("archivo").files[0];

    if (!archivo) {
        alert("Debe seleccionar un archivo.");
        return;
    }

    if (!window.crypto || !window.crypto.subtle) {
        alert("El navegador no permite calcular hashes en este contexto. Abrí la página desde http://localhost o HTTPS.");
        estado.textContent = "ERROR: API CRYPTO NO DISPONIBLE";
        return;
    }

    try {
        const buffer = await archivo.arrayBuffer();
        const hashBuffer = await window.crypto.subtle.digest("SHA-256", buffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashHex = hashArray
            .map(byte => byte.toString(16).padStart(2, "0"))
            .join("");

        const fechaActual = new Date();
        const fecha = fechaActual.toLocaleDateString();
        const hora = fechaActual.toLocaleTimeString();
        const tipoArchivo = archivo.type || "No informado";

        resultadoHash.value = hashHex;
        estado.textContent = "HASH CALCULADO CORRECTAMENTE";

        registro.innerHTML = `
<div class="cabecera">
    [ DOSSIER DE EVIDENCIA ]
</div>



<div class="metadatos">
    <div>FOR-TOOL-001</div>
    <div>ESTADO: VERIFICADO</div>
    <div>CLASIFICACIÓN: EVIDENCIA DIGITAL</div>
    <div>ALGORITMO: SHA256</div>
</div>

<div class="separador"></div>

<div class="titulo-seccion">
    [ IDENTIFICACIÓN ]
</div>

<div class="bloque">
    <span class="etiqueta">EXPEDIENTE</span>
    <span class="valor">${evidencia || "Sin informar"}</span>
</div>

<div class="bloque">
    <span class="etiqueta">RESPONSABLE</span>
    <span class="valor">${responsable || "Sin informar"}</span>
</div>

<div class="bloque">
    <span class="etiqueta">UBICACIÓN</span>
    <span class="valor">${ubicacion || "Sin informar"}</span>
</div>

<div class="bloque">
    <span class="etiqueta">ESTADO</span>
    <span class="valor">${estadoCustodia || "Sin informar"}</span>
</div>

<div class="bloque">
    <span class="etiqueta">RECEPCIÓN</span>
    <span class="valor">${fechaRecepcion || "Sin informar"}</span>
</div>

<div class="bloque">
    <span class="etiqueta">DESCRIPCIÓN</span>
    <span class="valor">${descripcion || "Sin informar"}</span>
</div>

<div class="bloque">
    <span class="etiqueta">FECHA DE REGISTRO</span>
    <span class="valor">${fecha} ${hora}</span>
</div>

<div class="separador"></div>

<div class="titulo-seccion">
    [ EVIDENCIA DIGITAL ]
</div>

<div class="bloque">
    <span class="etiqueta">ARCHIVO</span>
    <span class="valor">${archivo.name}</span>
</div>

<div class="bloque">
    <span class="etiqueta">TIPO</span>
    <span class="valor">${tipoArchivo}</span>
</div>

<div class="bloque">
    <span class="etiqueta">TAMAÑO</span>
    <span class="valor">${archivo.size} bytes</span>
</div>

<div class="separador"></div>

<div class="titulo-seccion">
    [ INTEGRIDAD ]
</div>

<div class="bloque">
    <span class="etiqueta">SHA256</span>
    <span class="valor hash">${hashHex}</span>
</div>
`;


    } catch (error) {
        console.error("ERROR AL CALCULAR HASH:", error);
        alert("No se pudo calcular el hash del archivo.");
        estado.textContent = "ERROR AL CALCULAR HASH";
    }
});

botonPDF.addEventListener("click", function () {
    if (!window.jspdf) {
        alert("No se pudo cargar el exportador PDF.");
        return;
    }

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    const contenido = registro.innerText.trim();
    const hashCalculado = resultadoHash.value.trim();
    const lineaDoble = "=".repeat(72);
    const lineaSimple = "-".repeat(72);
    const evidencia = document.getElementById("evidencia").value.trim() || "Sin informar";
    const responsable = document.getElementById("responsable").value.trim() || "Sin informar";
    const ubicacion = document.getElementById("ubicacion").value.trim() || "Sin informar";
    const estadoCustodia = document.getElementById("estadoCustodia").value.trim() || "Sin informar";
    const fechaRecepcion = document.getElementById("fechaRecepcion").value || "Sin informar";
    const descripcion = document.getElementById("descripcion").value.trim() || "Sin informar";
    const archivo = document.getElementById("archivo").files[0];
    const fechaEmision = new Date().toLocaleString();

    if (!hashCalculado) {
        alert("Primero calculá el hash para generar el registro.");
        return;
    }

    if (!contenido || contenido === "AÚN NO SE GENERÓ NINGÚN REGISTRO") {
        alert("Primero calculá el hash para generar el registro.");
        return;
    }

    const lineasPDF = [
        lineaDoble,
        "FORENSIA // FOR-TOOL-001",
        "GENERADOR DE CADENA DE CUSTODIA",
        lineaDoble,
        "",
        "[ IDENTIFICACION DE EVIDENCIA ]",
        lineaSimple,
        `EXPEDIENTE          : ${evidencia}`,
        `RESPONSABLE         : ${responsable}`,
        `UBICACION           : ${ubicacion}`,
        `ESTADO              : ${estadoCustodia}`,
        `FECHA DE RECEPCION  : ${fechaRecepcion}`,
        `FECHA DE EMISION    : ${fechaEmision}`,
        "",
        lineaDoble,
        "[ DESCRIPCION ]",
        lineaSimple,
        descripcion,
        "",
        lineaDoble,
        "[ ARCHIVO ANALIZADO ]",
        lineaSimple,
        `NOMBRE              : ${archivo.name}`,
        `TIPO                : ${archivo.type || "No informado"}`,
        `TAMANO              : ${archivo.size} bytes`,
        "",
        lineaDoble,
        "[ INTEGRIDAD DIGITAL ]",
        lineaSimple,
        "ALGORITMO           : SHA-256",
        `HASH                : ${hashCalculado}`,
        "",
        lineaDoble,
        "FIN DEL REGISTRO // CADENA DE CUSTODIA DIGITAL",
        lineaDoble
    ];

    doc.setFont("courier", "normal");
    doc.setFontSize(10);
    doc.text(lineasPDF.join("\n"), 10, 12, { maxWidth: 190 });
    doc.save("FORENSIA-Informe.pdf");
});

const botonVerificar =
    document.getElementById(
        "btnVerificar"
    );

if (botonVerificar) {

    botonVerificar.addEventListener(
        "click",
        async function () {

            const hashOriginal =
                document.getElementById(
                    "hashOriginal"
                ).value;

            console.log(
                "HASH ORIGINAL:",
                hashOriginal
            );

            const archivoVerificar =
                document.getElementById(
                    "archivoVerificar"
                ).files[0];

            console.log(
                "ARCHIVO:",
                archivoVerificar
            );

            const buffer =
                await archivoVerificar.arrayBuffer();

            const hashBuffer =
                await crypto.subtle.digest(
                    "SHA-256",
                    buffer
                );

            const hashArray =
                Array.from(
                    new Uint8Array(hashBuffer)
                );

            const hashNuevo =
                hashArray
                    .map(byte =>
                        byte.toString(16).padStart(2, "0")
                    )
                    .join("");

            console.log(
                "HASH NUEVO:",
                hashNuevo
            );

            if (
                hashOriginal.trim() ===
                hashNuevo.trim()
            ) {

                document.getElementById(
                    "resultadoVerificacion"
                ).textContent =
                    "✓ INTEGRIDAD CONSERVADA";

                document.getElementById(
                    "registroVerificacion"
                ).innerHTML = `

<div class="dossier">

    <div class="cabecera">

        [ VERIFICACIÓN DE INTEGRIDAD ]

    </div>

    <div class="separador"></div>

    <div class="bloque">

        <span class="etiqueta">
            HASH ESPERADO
        </span>

        <span class="valor">
            ${hashOriginal}
        </span>

    </div>

    <div class="bloque">

        <span class="etiqueta">
            HASH OBTENIDO
        </span>

        <span class="valor">
            ${hashNuevo}
        </span>

    </div>

    <div class="bloque">

        <span class="etiqueta">
            RESULTADO
        </span>

        <span class="valor">
            INTEGRIDAD CONSERVADA
        </span>

    </div>

</div>

`;

            } else {

                document.getElementById(
                    "resultadoVerificacion"
                ).textContent =
                    "⚠ ARCHIVO MODIFICADO";

                document.getElementById(
                    "registroVerificacion"
                ).innerHTML = `

    <div class="dossier">

        <div class="cabecera">

            [ VERIFICACIÓN DE INTEGRIDAD ]

        </div>

        <div class="separador"></div>

        <div class="bloque">

            <span class="etiqueta">
                HASH ESPERADO
            </span>

            <span class="valor">
                ${hashOriginal}
            </span>

        </div>

        <div class="bloque">

            <span class="etiqueta">
                HASH OBTENIDO
            </span>

            <span class="valor">
                ${hashNuevo}
            </span>

        </div>

        <div class="bloque">

            <span class="etiqueta">
                RESULTADO
            </span>

            <span class="valor error">
                ARCHIVO MODIFICADO
            </span>

        </div>

    </div>

    `;

            }

        }
    );

}

botonVerificar.addEventListener(
    "click",
    async function () {

        console.log(
            "VERIFICAR INTEGRIDAD"
        );

    }
);

const archivoVerificar =
    document.getElementById(
        "archivoVerificar"
    ).files[0];
