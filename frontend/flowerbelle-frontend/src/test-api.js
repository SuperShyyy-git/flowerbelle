import api from './services/api';

export const testConnection = async () => {
  try {
    console.log('Testing API connection...');
    console.log('API URL:', process.env.REACT_APP_API_URL);
    
    const response = await api.get('/auth/login/');
    console.log('✅ Connection successful:', response.data);
    return true;
  } catch (error) {
    console.error('❌ Connection failed:', error);
    if (error.response) {
      console.error('Response:', error.response.data);
      console.error('Status:', error.response.status);
    } else if (error.request) {
      console.error('No response received');
    } else {
      console.error('Error:', error.message);
    }
    return false;
  }
};