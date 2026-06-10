console.log("FORENSIA ONLINE");

const botonHash = document.getElementById("btnHash");
const botonPDF = document.getElementById("btnPDF");
const estado = document.getElementById("estado");
const registro = document.getElementById("registro");
const resultadoHash = document.getElementById("resultadoHash");
const botonCopiarHash = document.getElementById("btnCopiarHash");
const botonLimpiar = document.getElementById("btnLimpiar");

function actualizarEstado(mensaje, tipo) {
    estado.textContent = mensaje;
    estado.classList.remove(
        "estado-pendiente",
        "estado-correcto",
        "estado-alerta",
        "estado-error"
    );
    estado.classList.add(`estado-${tipo}`);
}

function actualizarResultadoVerificacion(mensaje, tipo) {
    const resultadoVerificacion = document.getElementById("resultadoVerificacion");

    if (!resultadoVerificacion) {
        return;
    }

    resultadoVerificacion.textContent = mensaje;
    resultadoVerificacion.classList.remove(
        "estado-pendiente",
        "estado-correcto",
        "estado-alerta",
        "estado-error"
    );
    resultadoVerificacion.classList.add(`estado-${tipo}`);
}

function marcarCampo(id, faltaDato) {
    const campo = document.getElementById(id);
    const fila = campo.closest(".field");

    if (!fila) {
        return;
    }

    fila.classList.toggle("field-warning", faltaDato);
}

function validarCamposMinimos() {
    const evidencia = document.getElementById("evidencia").value.trim();
    const responsable = document.getElementById("responsable").value.trim();
    const archivo = document.getElementById("archivo").files[0];
    const faltantes = [];

    if (!evidencia) {
        faltantes.push("numero de evidencia");
    }

    if (!responsable) {
        faltantes.push("responsable");
    }

    if (!archivo) {
        faltantes.push("archivo");
    }

    marcarCampo("evidencia", !evidencia);
    marcarCampo("responsable", !responsable);
    marcarCampo("archivo", !archivo);

    return faltantes;
}

["evidencia", "responsable", "archivo"].forEach(function (id) {
    const campo = document.getElementById(id);
    const evento = id === "archivo" ? "change" : "input";

    campo.addEventListener(evento, function () {
        const tieneDato = id === "archivo"
            ? campo.files.length > 0
            : campo.value.trim().length > 0;

        marcarCampo(id, !tieneDato);
    });
});

botonLimpiar.addEventListener("click", function () {
    [
        "evidencia",
        "responsable",
        "ubicacion",
        "estadoCustodia",
        "fechaRecepcion",
        "descripcion",
        "archivo",
        "resultadoHash",
        "hashOriginal",
        "archivoVerificar"
    ].forEach(function (id) {
        const campo = document.getElementById(id);

        if (campo) {
            campo.value = "";
        }
    });

    document.querySelectorAll(".field-warning").forEach(function (fila) {
        fila.classList.remove("field-warning");
    });

    registro.innerHTML = "AÚN NO SE GENERÓ NINGÚN REGISTRO";

    const resultadoVerificacion = document.getElementById("resultadoVerificacion");
    const registroVerificacion = document.getElementById("registroVerificacion");

    if (resultadoVerificacion) {
        actualizarResultadoVerificacion("SIN VERIFICAR", "pendiente");
    }

    if (registroVerificacion) {
        registroVerificacion.textContent = "SIN VERIFICACIONES";
    }

    actualizarEstado("SIN VERIFICAR", "pendiente");
});

botonHash.addEventListener("click", async function () {
    const evidencia = document.getElementById("evidencia").value.trim();
    const responsable = document.getElementById("responsable").value.trim();
    const ubicacion = document.getElementById("ubicacion").value.trim();
    const estadoCustodia = document.getElementById("estadoCustodia").value.trim();
    const fechaRecepcion = document.getElementById("fechaRecepcion").value;
    const descripcion = document.getElementById("descripcion").value.trim();
    const archivo = document.getElementById("archivo").files[0];
    const camposFaltantes = validarCamposMinimos();

    if (camposFaltantes.length > 0) {
        actualizarEstado(
            `DATOS MINIMOS PENDIENTES: ${camposFaltantes.join(", ").toUpperCase()}`,
            "alerta"
        );
    }

    if (!archivo) {
        alert("Debe seleccionar un archivo.");
        actualizarEstado("ERROR: ARCHIVO NO SELECCIONADO", "error");
        return;
    }

    if (!window.crypto || !window.crypto.subtle) {
        alert("El navegador no permite calcular hashes en este contexto. Abrí la página desde http://localhost o HTTPS.");
        actualizarEstado("ERROR: API CRYPTO NO DISPONIBLE", "error");
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

        if (camposFaltantes.length > 0) {
            actualizarEstado("HASH CALCULADO CON DATOS MINIMOS PENDIENTES", "alerta");
        } else {
            actualizarEstado("HASH CALCULADO CORRECTAMENTE", "correcto");
        }

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
        actualizarEstado("ERROR AL CALCULAR HASH", "error");
    }
});

botonCopiarHash.addEventListener("click", async function () {
    const hash = resultadoHash.value.trim();

    if (!hash) {
        alert("Primero calculá el hash.");
        actualizarEstado("SIN HASH PARA COPIAR", "error");
        return;
    }

    try {
        await navigator.clipboard.writeText(hash);
    } catch (error) {
        resultadoHash.select();
        document.execCommand("copy");
    }

    actualizarEstado("HASH COPIADO AL PORTAPAPELES", "correcto");
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
    const camposFaltantes = validarCamposMinimos();

    if (camposFaltantes.length > 0) {
        actualizarEstado(
            `PDF CON DATOS MINIMOS PENDIENTES: ${camposFaltantes.join(", ").toUpperCase()}`,
            "alerta"
        );
    }

    if (!hashCalculado) {
        alert("Primero calculá el hash para generar el registro.");
        return;
    }

    if (!contenido || contenido === "AÚN NO SE GENERÓ NINGÚN REGISTRO") {
        alert("Primero calculá el hash para generar el registro.");
        return;
    }

    if (!archivo) {
        alert("Debe seleccionar un archivo para exportar el informe.");
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

            if (!hashOriginal.trim()) {
                actualizarResultadoVerificacion(
                    "ALERTA: HASH ORIGINAL PENDIENTE",
                    "alerta"
                );
                return;
            }

            if (!archivoVerificar) {
                actualizarResultadoVerificacion(
                    "ALERTA: ARCHIVO A VERIFICAR PENDIENTE",
                    "alerta"
                );
                return;
            }

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

                actualizarResultadoVerificacion("INTEGRIDAD CONSERVADA", "correcto");

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

                actualizarResultadoVerificacion("ALERTA: ARCHIVO MODIFICADO", "alerta");

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

