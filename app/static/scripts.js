document.addEventListener("DOMContentLoaded", () => {
    const validateButton = document.getElementById("validate-cpf-btn");
    const inputCpf = document.getElementById("cpf");
    const storedCpf = document.getElementById("stored-cpf").textContent;

    validateButton.addEventListener("click", async (event) => {
        event.preventDefault();

        const cpf = inputCpf.value.replace(/\D/g, ''); // Remove caracteres não numéricos

        if (cpf.length !== 11) {
            displayMessage("CPF inválido. Verifique o valor inserido.", "error");
            inputCpf.style.border = "2px solid red";
            return;
        }

        try {
            const response = await fetch('/validate-cpf', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    cpf: cpf,
                    stored_cpf: storedCpf
                })
            });

            const result = await response.json();

            if (response.ok) {
                displayMessage("CPF validado com sucesso!", "success");
                inputCpf.style.border = "2px solid green";
            } else {
                displayMessage("CPF não cadastrado.", "error");
                inputCpf.style.border = "2px solid red";
            }
        } catch (error) {
            console.error("Erro ao validar CPF:", error);
            displayMessage("Erro ao validar CPF. Tente novamente.", "error");
        }
    });

    function displayMessage(message, type) {
        const messageBox = document.getElementById("message-box");
        messageBox.textContent = message;
        messageBox.className = type === "success" ? "message-success" : "message-error";
        messageBox.style.display = "block";
    }
});

// document.addEventListener("DOMContentLoaded", () => {
//     const validateButton = document.getElementById("validate-cpf-btn");
//     const inputCpf = document.getElementById("cpf");
//     const storedCpf = document.getElementById("stored-cpf").textContent;

//     validateButton.addEventListener("click", async (event) => {
//         event.preventDefault(); // Impede o envio do formulário

//         const cpf = inputCpf.value.replace(/\D/g, ''); // Remove caracteres não numéricos do CPF

//         try {
//             const response = await fetch('/validate-cpf', {
//                 method: 'POST',
//                 headers: {
//                     'Content-Type': 'application/json',
//                 },
//                 body: JSON.stringify({
//                     cpf: cpf,
//                     stored_cpf: storedCpf
//                 })
//             });

//             const result = await response.json();

//             if (response.ok) {
//                 // Exibe uma mensagem de sucesso com um check
//                 alert("CPF Validado!");
//                 inputCpf.style.border = "2px solid green"; // Exemplo de estilo para indicar sucesso
//             } else {
//                 // Exibe uma mensagem de erro
//                 alert("CPF Não Cadastrado");
//                 inputCpf.style.border = "2px solid red"; // Exemplo de estilo para indicar erro
//             }
//         } catch (error) {
//             console.error("Erro ao validar CPF:", error);
//             alert("Erro ao validar CPF. Tente novamente.");
//         }
//     });
// });
