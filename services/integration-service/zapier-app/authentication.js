/**
 * MAMS Zapier App Authentication
 */

const testAuth = async (z, bundle) => {
  const response = await z.request({
    url: `${bundle.authData.baseUrl}/api/v1/integrations/zapier/auth/test`,
    method: 'GET'
  });
  
  if (response.status !== 200) {
    throw new z.errors.Error('Authentication failed', 'AuthenticationError', response.status);
  }
  
  return response.json;
};

module.exports = {
  type: 'custom',
  
  fields: [
    {
      key: 'baseUrl',
      label: 'MAMS Instance URL',
      type: 'string',
      required: true,
      helpText: 'The base URL of your MAMS instance (e.g., https://mams.company.com)'
    },
    {
      key: 'apiKey',
      label: 'API Key',
      type: 'string',
      required: true,
      helpText: 'Your MAMS API key from the integrations settings'
    }
  ],
  
  test: testAuth,
  
  connectionLabel: (z, bundle) => {
    return `MAMS (${bundle.authData.baseUrl})`;
  }
};