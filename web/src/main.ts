import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import VxeUI from "vxe-table";
import "vxe-table/lib/style.css";
import App from "./App.vue";
import { router } from "./router";
import "./styles/tokens.css";
import "./styles/global.css";

createApp(App)
  .use(createPinia())
  .use(router)
  .use(ElementPlus)
  .use(VxeUI)
  .mount("#app");
