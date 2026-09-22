import { z } from "zod";

export const chatIdSchema = z
  .string()
  .uuid({ message: "Invalid Chat ID format" });

export const askQuestionSchema = z.object({
  chatId: z.string().uuid({ message: "Invalid or missing Chat ID" }),
  question: z
    .string({ required_error: "Question is required" })
    .trim()
    .min(1, { message: "Question cannot be empty" })
    .max(2000, { message: "Question must not exceed 2000 characters" }),
});

export const pdfUploadSchema = z.object({
  file: z
    .custom((val) => typeof window !== "undefined" && val instanceof File, {
      message: "A valid file is required",
    })
    .refine((file) => file && file.name?.toLowerCase().endsWith(".pdf"), {
      message: "Only PDF files (.pdf) are supported",
    })
    .refine((file) => file && file.size > 0, {
      message: "File cannot be empty",
    })
    .refine((file) => file && file.size <= 50 * 1024 * 1024, {
      message: "File size must be under 50MB",
    }),
  chatId: z.string().uuid({ message: "Invalid Chat ID" }).optional().nullable(),
});
