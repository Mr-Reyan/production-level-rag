import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  askQuestion,
  uploadPdf,
  fetchChats,
  fetchChatDetail,
  deleteChat,
} from "../lib/api";

export function useChats() {
  return useQuery({
    queryKey: ["chats"],
    queryFn: fetchChats,
  });
}

export function useChatDetail(chatId) {
  return useQuery({
    queryKey: ["chat", chatId],
    queryFn: () => fetchChatDetail(chatId),
    enabled: !!chatId,
  });
}

export function useUploadPdf() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ file, chatId }) => uploadPdf(file, chatId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["chats"] });
      if (data?.chat_id) {
        queryClient.invalidateQueries({ queryKey: ["chat", data.chat_id] });
      }
    },
  });
}

export function useAsk() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ chatId, question }) => askQuestion(chatId, question),
    onSuccess: (_, variables) => {
      if (variables?.chatId) {
        queryClient.invalidateQueries({ queryKey: ["chat", variables.chatId] });
      }
    },
  });
}

export function useDeleteChat() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (chatId) => deleteChat(chatId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chats"] });
    },
  });
}