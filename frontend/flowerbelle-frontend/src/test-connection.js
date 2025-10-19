import api from './services/api';

export const testBackendConnection = async () => {
  console.log('🧪 Testing Backend Connection...');
  console.log('📍 API URL:', process.env.REACT_APP_API_URL);
  
  try {
    // Test 1: Check if backend is reachable
    const response = await api.get('/auth/login/');
    console.log('✅ Backend is reachable!');
    console.log('Response:', response.data);
    return true;
  } catch (error) {
    console.error('❌ Connection failed!');
    
    if (error.code === 'ERR_NETWORK') {
      console.error('Network Error: Backend is not running or URL is wrong');
      console.error('Make sure Django is running on http://127.0.0.1:8000');
    } else if (error.response?.status === 405) {
      console.log('✅ Backend is reachable (405 is expected for GET on login endpoint)');
      return true;
    } else {
      console.error('Error:', error.message);
      console.error('Status:', error.response?.status);
      console.error('Data:', error.response?.data);
    }
    
    return false;
  }
};