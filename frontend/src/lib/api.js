import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const http = axios.create({ baseURL: API, headers: { "Content-Type": "application/json" } });

export const api = {
  telephonyStatus: () => http.get("/telephony/status").then((r) => r.data),
  scenarios: () => http.get("/simulator/scenarios").then((r) => r.data),
  createContract: (request_text) => http.post("/contracts", { request_text }).then((r) => r.data),
  getContract: (id) => http.get(`/contracts/${id}`).then((r) => r.data),
  updateContract: (id, payload) => http.put(`/contracts/${id}`, payload).then((r) => r.data),
  consent: (id, granted, recipient_number = "") =>
    http.post(`/contracts/${id}/consent`, { granted, recipient_number }).then((r) => r.data),
  revoke: (id) => http.post(`/contracts/${id}/revoke`).then((r) => r.data),
  execute: (id, mode, scenario, recipient_number = "") =>
    http.post(`/contracts/${id}/execute`, { mode, scenario, recipient_number }).then((r) => r.data),
  getCall: (id) => http.get(`/calls/${id}`).then((r) => r.data),
};
