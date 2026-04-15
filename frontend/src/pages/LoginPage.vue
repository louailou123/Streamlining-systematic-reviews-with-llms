<template>
  <AuthShell
    eyebrow="Welcome Back"
    title="Sign in to your workspace"
    description="Pick up your review where you left it and keep the pipeline moving with clear approvals and live updates."
  >
    <Message v-if="error" severity="error" class="w-full">
      {{ error }}
    </Message>

    <div class="flex flex-column gap-4">
      <div class="flex flex-column gap-2">
        <label for="login-email" class="text-sm font-semibold">Email</label>
        <InputText
          id="login-email"
          v-model="email"
          type="email"
          placeholder="you@example.com"
          autocomplete="email"
        />
      </div>

      <div class="flex flex-column gap-2">
        <label for="login-password" class="text-sm font-semibold">Password</label>
        <Password
          id="login-password"
          v-model="password"
          input-class="w-full"
          toggle-mask
          :feedback="false"
          placeholder="Enter your password"
          autocomplete="current-password"
        />
      </div>

      <Button
        label="Sign in"
        icon="pi pi-arrow-right"
        icon-pos="right"
        :loading="authStore.isLoading"
        @click="handleSubmit"
      />

      <Divider align="center">or</Divider>

      <Button
        label="Continue with Google"
        severity="secondary"
        :loading="googleLoading"
        @click="handleGoogleLogin"
      />
    </div>

    <p class="auth-footnote">
      New to LiRA?
      <RouterLink class="auth-link ml-1" to="/register">
        Create an account
      </RouterLink>
    </p>
  </AuthShell>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import Button from 'primevue/button';
import Divider from 'primevue/divider';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import Password from 'primevue/password';

import { authApi } from '@/api/auth';
import AuthShell from '@/components/auth/AuthShell.vue';
import { getErrorMessage } from '@/lib/workflow';
import { useAuthStore } from '@/stores/auth';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const email = ref('');
const password = ref('');
const error = ref('');
const googleLoading = ref(false);

function resolveRedirect() {
  const redirect = route.query.redirect;
  return typeof redirect === 'string' && redirect.trim() ? redirect : '/';
}

async function handleSubmit() {
  if (!email.value.trim() || !password.value) {
    return;
  }

  error.value = '';

  try {
    await authStore.login(email.value.trim(), password.value);
    await router.push(resolveRedirect());
  } catch (err) {
    error.value = getErrorMessage(err, 'Login failed. Please try again.');
  }
}

async function handleGoogleLogin() {
  error.value = '';
  googleLoading.value = true;

  try {
    const url = await authApi.getGoogleLoginUrl();
    window.location.href = url;
  } catch (err) {
    googleLoading.value = false;
    error.value = getErrorMessage(err, 'Google login is not configured yet.');
  }
}
</script>

<style scoped>
.auth-footnote {
  margin: 0;
  color: var(--app-text-soft);
  line-height: 1.7;
}

.auth-link {
  font-weight: 700;
}
</style>
