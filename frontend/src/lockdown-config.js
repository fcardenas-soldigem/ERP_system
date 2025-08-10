// Configuración para SES (Secure ECMAScript)
const lockdownOptions = {
  errorTaming: 'unsafe',
  consoleTaming: 'unsafe',
  mathTaming: 'unsafe',
  dateTaming: 'unsafe',
  overrideTaming: 'severe'
};

export default lockdownOptions; 