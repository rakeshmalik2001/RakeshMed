"use client";

import type { Route } from "next";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AUTH_LOGIN_PHONE_STORAGE_KEY, AUTH_REDIRECT_STORAGE_KEY, sendOtp } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [phoneNumber, setPhoneNumber] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  async function handleSendOtp() {
    setErrorMessage("");
    setSuccessMessage("");

    const normalizedPhone = phoneNumber.replace(/\D/g, "");
    if (normalizedPhone.length < 10) {
      setErrorMessage("Enter a valid mobile number.");
      return;
    }

    setSubmitting(true);

    try {
      await sendOtp({ phone_number: normalizedPhone, purpose: "login" });
      setSuccessMessage("OTP sent successfully.");
      const params = new URLSearchParams(window.location.search);
      const nextPath =
        window.sessionStorage.getItem(AUTH_REDIRECT_STORAGE_KEY) ||
        params.get("next") ||
        "/account";
      window.sessionStorage.setItem(AUTH_LOGIN_PHONE_STORAGE_KEY, normalizedPhone);
      window.sessionStorage.setItem(AUTH_REDIRECT_STORAGE_KEY, nextPath);
      router.push("/verify-otp" as Route);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not send OTP.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page-shell auth-page-shell">
      <section className="auth-card">
        <div className="auth-copy">
          <p className="eyebrow">Authentication</p>
          <h1>Login with OTP</h1>
          <p>
            Sign in with your mobile number to continue with prescription uploads, cart,
            checkout, and order tracking.
          </p>
          <ul className="clean-list auth-list">
            <li>Secure OTP-based login</li>
            <li>Works for customer prescription uploads</li>
            <li>Session token stored locally for API access</li>
          </ul>
        </div>

        <div className="auth-form-card">
          <label className="rx-field">
            <span>Mobile number</span>
            <input
              data-testid="login-phone-input"
              type="tel"
              value={phoneNumber}
              onChange={(event) => setPhoneNumber(event.target.value)}
              placeholder="Enter 10-digit mobile number"
            />
          </label>

          <div className="auth-inline-message">
            {errorMessage ? <span className="auth-error">{errorMessage}</span> : null}
            {!errorMessage && successMessage ? <span className="auth-success">{successMessage}</span> : null}
          </div>

          <button data-testid="send-otp-button" type="button" className="primary-action auth-submit" onClick={handleSendOtp} disabled={submitting}>
            {submitting ? "Sending OTP..." : "Send OTP"}
          </button>
        </div>
      </section>
    </main>
  );
}
