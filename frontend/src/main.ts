import { createApp } from 'vue';
import PrimeVue from 'primevue/config';
import ToastService from 'primevue/toastservice';
import { createPinia } from 'pinia';

import App from './App.vue';
import { createAppRouter } from './router';
import { liraPreset } from './theme/preset';
import { useAuthStore } from './stores/auth';
import { useTheme } from './composables/useTheme';

import 'primeicons/primeicons.css';
import 'primeflex/primeflex.css';
import './styles/base.css';

const app = createApp(App);
const pinia = createPinia();
const router = createAppRouter(pinia);

app.use(pinia);
app.use(router);
app.use(ToastService);
app.use(PrimeVue, {
  ripple: true,
  theme: {
    preset: liraPreset,
    options: {
      darkModeSelector: '.app-dark',
    },
  },
});

useTheme();

const authStore = useAuthStore(pinia);

authStore.initialize().finally(async () => {
  await router.isReady();
  app.mount('#app');
});
