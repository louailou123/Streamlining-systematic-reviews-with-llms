<template>
  <AuthShell
    eyebrow="Connecting Account"
    title="Completing your sign in"
    description="We are finalizing your session and preparing the workspace."
  >
    <div class="callback-state">
      <ProgressSpinner stroke-width="4" style="width: 3rem; height: 3rem" />
      <div class="flex flex-column gap-2 text-center">
        <div class="text-lg font-semibold">Signing you in</div>
        <p class="m-0 app-subheading">
          Your account has been verified. You will be redirected as soon as your profile is ready.
        </p>
      </div>
      <Message v-if="error" severity="error" class="w-full">
        {{ error }}
      </Message>
    </div>
  </AuthShell>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Message from 'primevue/message';
import ProgressSpinner from 'primevue/progressspinner';

import AuthShell from '@/components/auth/AuthShell.vue';
import { getErrorMessage } from '@/lib/workflow';
import { useAuthStore } from '@/stores/auth';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const error = ref('');

onMounted(async () => {
  const accessToken = route.query.access_token;
  const refreshToken = route.query.refresh_token;

  if (typeof accessToken !== 'string' || typeof refreshToken !== 'string') {
    await router.replace('/login');
    return;
  }

  try {
    authStore.setTokens(accessToken, refreshToken);
    await authStore.loadUser();
    await router.replace('/');
  } catch (err) {
    error.value = getErrorMessage(err, 'Unable to complete sign in.');
    window.localStorage.removeItem('access_token');
    window.localStorage.removeItem('refresh_token');
    window.setTimeout(() => {
      router.replace('/login').catch(() => {
        // no-op
      });
    }, 1200);
  }
});
</script>

<style scoped>
.callback-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem 0 0.25rem;
}
</style>
