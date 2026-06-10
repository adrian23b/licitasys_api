const state = {
  apiBase: "http://localhost:8000",
  token: null,
  mode: "wallet",
  walletAddress: null,
  explorerUrl: null,
  step: "auth",
};

const els = {
  apiBase: document.getElementById("apiBase"),
  authBtn: document.getElementById("authBtn"),
  connectWalletBtn: document.getElementById("connectWalletBtn"),
  walletMethodBtn: document.getElementById("walletMethodBtn"),
  emailMethodBtn: document.getElementById("emailMethodBtn"),
  walletMethodPanel: document.getElementById("walletMethodPanel"),
  emailMethodPanel: document.getElementById("emailMethodPanel"),
  companyName: document.getElementById("companyName"),
  ruc: document.getElementById("ruc"),
  email: document.getElementById("email"),
  companyEmail: document.getElementById("companyEmail"),
  walletAddress: document.getElementById("walletAddress"),
  statusBox: document.getElementById("statusBox"),
  explorerLinkBox: document.getElementById("explorerLinkBox"),
  tokenOutput: document.getElementById("tokenOutput"),
  authPanel: document.getElementById("authPanel"),
  companyPanel: document.getElementById("companyPanel"),
  resultPanel: document.getElementById("resultPanel"),
  profileForm: document.getElementById("profileForm"),
  profileSubmitBtn: document.getElementById("profileSubmitBtn"),
  copyTokenBtn: document.getElementById("copyTokenBtn"),
};

function setStatus(message, isError = false) {
  els.statusBox.textContent = message;
  els.statusBox.classList.toggle("error", isError);
}

function setStep(step) {
  state.step = step;
  document.querySelectorAll(".step").forEach((stepNode) => {
    stepNode.classList.toggle("is-active", stepNode.dataset.step === step);
  });

  els.authPanel.classList.toggle("hidden", step !== "auth");
  els.companyPanel.classList.toggle("hidden", step !== "company");
  els.resultPanel.classList.toggle("hidden", step !== "result");
}

function showExplorerLink(url) {
  state.explorerUrl = url || null;
  if (!url) {
    els.explorerLinkBox.innerHTML = "";
    els.explorerLinkBox.classList.add("hidden");
    return;
  }

  els.explorerLinkBox.classList.remove("hidden");
  els.explorerLinkBox.innerHTML = `
    <div class="info-pill">✓ Anclaje en blockchain listo</div>
    <a href="${url}" target="_blank" rel="noopener noreferrer">Ver transacción en el explorador</a>
  `;
}

function resetAccessState() {
  state.token = null;
  state.explorerUrl = null;
  els.tokenOutput.value = "";
  els.walletAddress.value = "";
  state.walletAddress = null;
  localStorage.removeItem("seace_access_token");
}

function readTokenFromStorage() {
  const token = localStorage.getItem("seace_access_token");
  if (token) {
    state.token = token;
    els.tokenOutput.value = token;
    setStatus("Cuenta ya creada. Completa la empresa para finalizar.");
    setStep("company");
  }
}

function setRegistrationMode(mode) {
  state.mode = mode;
  els.walletMethodBtn.classList.toggle("active", mode === "wallet");
  els.emailMethodBtn.classList.toggle("active", mode === "email");
  els.walletMethodPanel.classList.toggle("hidden", mode !== "wallet");
  els.emailMethodPanel.classList.toggle("hidden", mode !== "email");
}

function showCompanyForm(email = "") {
  els.companyEmail.value = email;
  setStep("company");
}

async function connectWallet() {
  if (!window.ethereum) {
    setStatus("MetaMask no está instalado. Instálalo para continuar con wallet.", true);
    return;
  }

  try {
    const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
    if (!accounts?.length) {
      throw new Error("No se seleccionó ninguna wallet.");
    }

    state.walletAddress = accounts[0].toLowerCase();
    els.walletAddress.value = state.walletAddress;
    setStatus(`Wallet conectada: ${state.walletAddress}`);
  } catch (error) {
    setStatus(error.message || "No se pudo conectar la wallet", true);
  }
}

async function registerAndAuth() {
  state.apiBase = els.apiBase.value.trim() || "http://localhost:8000";

  try {
    if (state.mode === "wallet") {
      if (!state.walletAddress) {
        setStatus("Conecta una wallet antes de continuar.", true);
        return;
      }

      setStatus("Registrando con wallet...");
      const registerRes = await fetch(`${state.apiBase}/identity/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ wallet_address: state.walletAddress }),
      });

      const registerData = await registerRes.json().catch(() => ({}));
      if (!registerRes.ok) {
        throw new Error(registerData.detail || "No se pudo registrar la wallet.");
      }

      setStatus("Generando acceso para la wallet...");
      const nonceRes = await fetch(`${state.apiBase}/identity/nonce`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ wallet_address: state.walletAddress }),
      });

      const nonceData = await nonceRes.json().catch(() => ({}));
      if (!nonceRes.ok) {
        throw new Error(nonceData.detail || "No se pudo obtener el nonce.");
      }

      const signature = await signMessage(nonceData.message);
      const verifyRes = await fetch(`${state.apiBase}/identity/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          wallet_address: state.walletAddress,
          nonce: nonceData.nonce,
          signature,
        }),
      });

      const verifyData = await verifyRes.json().catch(() => ({}));
      if (!verifyRes.ok) {
        throw new Error(verifyData.detail || "No se pudo verificar la identidad.");
      }

      state.token = verifyData.access_token;
      localStorage.setItem("seace_access_token", state.token);
      els.tokenOutput.value = state.token;
      const explorerUrl = verifyData.explorer_url || (verifyData.identity?.verification_tx_hash ? `https://explorer.zktanenbaum.io/tx/${verifyData.identity.verification_tx_hash}` : null);
      showExplorerLink(explorerUrl);
      showCompanyForm(verifyData.identity?.corporate_email || "");
      setStatus("Cuenta creada correctamente. Completa los datos de la empresa.");
      return;
    }

    const corporateEmail = els.email.value.trim();
    if (!corporateEmail) {
      setStatus("Ingresa un correo corporativo para registrar con email.", true);
      return;
    }

    setStatus("Creando la cuenta y generando la wallet custodial...");
    const registerRes = await fetch(`${state.apiBase}/identity/register-custodial`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ corporate_email: corporateEmail }),
    });

    const registerData = await registerRes.json().catch(() => ({}));
    if (!registerRes.ok) {
      throw new Error(registerData.detail || "No se pudo crear la cuenta con email.");
    }

    state.token = registerData.access_token;
    localStorage.setItem("seace_access_token", state.token);
    els.walletAddress.value = registerData.wallet_address;
    els.tokenOutput.value = state.token;
    showExplorerLink(registerData.explorer_url || null);
    showCompanyForm(registerData.identity?.corporate_email || corporateEmail);
    setStatus(`Cuenta creada correctamente. Wallet: ${registerData.wallet_address}`);
  } catch (error) {
    showExplorerLink(null);
    setStatus(error.message || "Error inesperado", true);
  }
}

async function completeProfile() {
  if (!state.token) {
    setStatus("Primero debes registrar la cuenta.", true);
    return;
  }

  const payload = {
    company_name: els.companyName.value.trim(),
    ruc: els.ruc.value.trim(),
    corporate_email: els.companyEmail.value.trim(),
  };

  if (!payload.company_name || !payload.ruc || !payload.corporate_email) {
    setStatus("Completa nombre, RUC y correo para guardar la empresa.", true);
    return;
  }

  try {
    setStatus("Guardando los datos de la empresa...");
    const response = await fetch(`${state.apiBase}/identity/me`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${state.token}`,
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "No se pudo guardar la empresa.");
    }

    setStatus("Empresa guardada correctamente.");
    setStep("result");
  } catch (error) {
    setStatus(error.message || "Error inesperado", true);
  }
}

async function signMessage(message) {
  if (!window.ethereum) {
    throw new Error("MetaMask no está disponible");
  }

  const from = state.walletAddress;
  if (!from) {
    throw new Error("No hay una wallet conectada");
  }

  const signature = await window.ethereum.request({
    method: "personal_sign",
    params: [message, from],
  });

  return signature;
}

async function copyToken() {
  if (!state.token) {
    setStatus("Aún no hay un código de acceso para copiar.", true);
    return;
  }

  try {
    await navigator.clipboard.writeText(state.token);
    setStatus("Código de acceso copiado al portapapeles.");
  } catch (error) {
    setStatus("No se pudo copiar el código, cópialo manualmente.", true);
  }
}

function wireEvents() {
  els.connectWalletBtn.addEventListener("click", connectWallet);
  els.walletMethodBtn.addEventListener("click", () => setRegistrationMode("wallet"));
  els.emailMethodBtn.addEventListener("click", () => setRegistrationMode("email"));
  els.authBtn.addEventListener("click", (event) => {
    event.preventDefault();
    registerAndAuth();
  });
  els.profileSubmitBtn.addEventListener("click", (event) => {
    event.preventDefault();
    completeProfile();
  });
  els.copyTokenBtn.addEventListener("click", copyToken);
  els.apiBase.addEventListener("change", () => {
    state.apiBase = els.apiBase.value.trim() || "http://localhost:8000";
  });
}

window.addEventListener("DOMContentLoaded", () => {
  wireEvents();
  setRegistrationMode("wallet");
  setStep("auth");
  readTokenFromStorage();
  if (!state.token) {
    setStatus("Selecciona cómo iniciar sesión para comenzar.");
  }
  showExplorerLink(null);

  if (window.ethereum) {
    window.ethereum.on("accountsChanged", (accounts) => {
      if (!accounts?.length) {
        resetAccessState();
        setStep("auth");
        setStatus("Wallet desconectada. Conecta otra para continuar.");
        return;
      }
      state.walletAddress = accounts[0].toLowerCase();
      els.walletAddress.value = state.walletAddress;
      setStatus(`Wallet conectada: ${state.walletAddress}`);
    });
  }
});
