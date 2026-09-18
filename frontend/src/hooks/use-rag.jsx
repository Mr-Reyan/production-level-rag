import { useMutation } from "@tanstack/react-query";
import { askQuestion, uploadPdf } from "../lib/api";

export function useUploadPdf() {
  return useMutation({
    mutationFn: (file) => uploadPdf(file),
  });
}

export function useAsk() {
  return useMutation({
    mutationFn: (question) => askQuestion(question),
  });
}