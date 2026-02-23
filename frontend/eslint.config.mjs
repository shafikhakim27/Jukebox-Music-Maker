import nextVitals from 'eslint-config-next/core-web-vitals.js';
import nextTypescript from 'eslint-config-next/typescript.js';

const toArray = (config) => (Array.isArray(config) ? config : [config]);

export default [...toArray(nextVitals), ...toArray(nextTypescript)];
