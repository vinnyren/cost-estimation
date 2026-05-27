import{a as p}from"./index-rWwaapY5.js";const o={effective:a=>p.get(`/api/projects/${a}/params/effective`),global:()=>p.get("/api/params/global"),patchGlobal:(a,e)=>p.patch("/api/params/global",{key:a,value:e}),resetGlobal:()=>p.post("/api/params/global/reset"),override:(a,e)=>p.patch(`/api/projects/${a}/params/override`,e)};export{o as p};
//# sourceMappingURL=params-D9PA_odv.js.map
