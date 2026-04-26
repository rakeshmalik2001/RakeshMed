"use client";

import type { Route } from "next";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  AUTH_LOGIN_PHONE_STORAGE_KEY,
  AUTH_REDIRECT_STORAGE_KEY,
  verifyOtp
} from "@/lib/api";
import { getDashboardPathForRole } from "@/lib/role-dashboard";

export default function VerifyOtpPage() {
  const router = useRouter();
  const [otpCode, setOtpCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [phoneNumber, setPhoneNumber] = useState(() => {
    if (typeof window === "undefined") {
      return "";
    }

    const params = new URLSearchParams(window.location.search);
    return window.sessionStorage.getItem(AUTH_LOGIN_PHONE_STORAGE_KEY) || params.get("phone") || "";
  });
  const [nextPath, setNextPath] = useState(() => {
    if (typeof window === "undefined") {
      return "/account";
    }

    const params = new URLSearchParams(window.location.search);
    return window.sessionStorage.getItem(AUTH_REDIRECT_STORAGE_KEY) || params.get("next") || "/account";
  });

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const queryPhone = params.get("phone") || "";
    const queryNext = params.get("next") || "/account";
    const storedPhone = window.sessionStorage.getItem(AUTH_LOGIN_PHONE_STORAGE_KEY) || queryPhone;
    const storedNext = window.sessionStorage.getItem(AUTH_REDIRECT_STORAGE_KEY) || queryNext;
    setPhoneNumber(storedPhone);
    setNextPath(storedNext);
  }, []);

  const resolvedPhoneNumber =
    phoneNumber ||
    (typeof window !== "undefined"
      ? window.sessionStorage.getItem(AUTH_LOGIN_PHONE_STORAGE_KEY) || new URLSearchParams(window.location.search).get("phone") || ""
      : "");
  const resolvedNextPath =
    nextPath ||
    (typeof window !== "undefined"
      ? window.sessionStorage.getItem(AUTH_REDIRECT_STORAGE_KEY) || new URLSearchParams(window.location.search).get("next") || "/account"
      : "/account");

  async function handleVerifyOtp() {
    setErrorMessage("");
    setSuccessMessage("");

    if (!resolvedPhoneNumber) {
      setErrorMessage("Phone number is missing. Go back and request a new OTP.");
      return;
    }

    const normalizedCode = otpCode.trim();
    if (normalizedCode.length !== 6) {
      setErrorMessage("Enter the 6-digit OTP.");
      return;
    }

    setSubmitting(true);

    try {
      const response = await verifyOtp({
        phone_number: resolvedPhoneNumber,
        otp_code: normalizedCode,
        purpose: "login"
      });
      setSuccessMessage(`Welcome${response.user.full_name ? `, ${response.user.full_name}` : ""}.`);
      window.sessionStorage.removeItem(AUTH_LOGIN_PHONE_STORAGE_KEY);
      window.sessionStorage.removeItem(AUTH_REDIRECT_STORAGE_KEY);
      const targetPath = resolvedNextPath === "/account" ? getDashboardPathForRole(response.user.role) : resolvedNextPath;
      router.push(targetPath as Route);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not verify OTP.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page-shell auth-page-shell">
      <section className="auth-card">
        <div className="auth-copy">
          <p className="eyebrow">Authentication</p>
          <h1>Verify one-time password</h1>
          <p>
            Enter the OTP sent to <strong suppressHydrationWarning>{resolvedPhoneNumber || "your mobile number"}</strong> to complete login.
          </p>
          <ul className="clean-list auth-list">
            <li>OTP expires quickly for safety</li>
            <li>Use the latest OTP sent</li>
            <li>Successful verification stores your API auth token locally</li>
          </ul>
        </div>

        <div className="auth-form-card">
          <label className="rx-field">
            <span>6-digit OTP</span>
            <input
              data-testid="verify-otp-input"
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={otpCode}
              onChange={(event) => setOtpCode(event.target.value.replace(/\D/g, ""))}
              placeholder="Enter OTP"
            />
          </label>

          <div className="auth-inline-message">
            {errorMessage ? <span className="auth-error">{errorMessage}</span> : null}
            {!errorMessage && successMessage ? <span className="auth-success">{successMessage}</span> : null}
          </div>

          <button data-testid="verify-otp-button" type="button" className="primary-action auth-submit" onClick={handleVerifyOtp} disabled={submitting}>
            {submitting ? "Verifying..." : "Verify OTP"}
          </button>
        </div>
      </section>
    </main>
  );
}
