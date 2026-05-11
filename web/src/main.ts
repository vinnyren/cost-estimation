import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import { router, extractTokenFromUrl } from "./router";
import "./styles/tokens.css";
import "./styles/global.css";

extractTokenFromUrl();

createApp(App)
  .use(createPinia())
  .use(router)
  .mount("#app");
