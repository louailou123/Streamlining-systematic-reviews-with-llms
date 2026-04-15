<template>
  <AuthShell
    eyebrow="Create Account"
    title="Set up your research workspace"
    description="Create a secure account to launch reviews, inspect each step, and keep your approval decisions visible."
  >
    <Message v-if="error" severity="error" class="w-full">
      {{ error }}
    </Message>

    <div class="register-grid">
      <div class="flex flex-column gap-2">
        <label for="register-full-name" class="text-sm font-semibold">Full name</label>
        <InputText
          id="register-full-name"
          v-model="fullName"
          placeholder="Jane Doe"
          autocomplete="name"
        />
      </div>

      <div class="flex flex-column gap-2">
        <label for="register-username" class="text-sm font-semibold">Username</label>
        <InputText
          id="register-username"
          v-model="username"
          placeholder="janedoe"
          autocomplete="username"
        />
      </div>
    </div>

    <div class="flex flex-column gap-4">
      <div class="flex flex-column gap-2">
        <label for="register-email" class="text-sm font-semibold">Email</label>
        <InputText
          id="register-email"
          v-model="email"
          type="email"
          placeholder="you@example.com"
          autocomplete="email"
        />
      </div>

      <div class="flex flex-column gap-2">
        <label for="register-password" class="text-sm font-semibold">Password</label>
        <Password
          id="register-password"
          v-model="password"
          input-class="w-full"
          toggle-mask
          :feedback="false"
          placeholder="Create a strong password"
          autocomplete="new-password"
        />
      </div>

      <Button
        label="Create account"
        icon="pi pi-arrow-right"
        icon-pos="right"
        :loading="authStore.isLoading"
        @click="handleSubmit"
      />
    </div>

    <p class="auth-footnote">
      Already have an account?
      <RouterLink class="auth-link ml-1" to="/login">
        Sign in
      </RouterLink>
    </p>
  </AuthShell>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import Password from 'primevue/password';

import AuthShell from '@/components/auth/AuthShell.vue';
import { getErrorMessage } from '@/lib/workflow';
import { useAuthStore } from '@/stores/auth';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const email = ref('');
const password = ref('');
const username = ref('');
const fullName = ref('');
const error = ref('');

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
    await authStore.register(
      email.value.trim(),
      password.value,
      username.value.trim() || undefined,
      fullName.value.trim() || undefined,
    );
    await router.push(resolveRedirect());
  } catch (err) {
    error.value = getErrorMessage(err, 'Registration failed. Please try again.');
  }
}
</script>

<style scoped>
.register-grid {
  display: grid;
  gap: 1rem;
}

.auth-footnote {
  margin: 0;
  color: var(--app-text-soft);
  line-height: 1.7;
}

.auth-link {
  font-weight: 700;
}

@media (min-width: 720px) {
  .register-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
