"use client";

import React from 'react';
import { useGoogleLogin } from '@react-oauth/google';
import { useAuth } from './AuthContext';
import { Button } from '@mui/material';

export default function GoogleLoginButton() {
  const { loginWithCode } = useAuth();
  
  const handleLogin = useGoogleLogin({
    onSuccess: (tokenResponse) => {
      loginWithCode(tokenResponse.code);
    },
    onError: () => {
      // OAuth login failed; errors are handled by the auth layer
    },
    flow: 'auth-code',
    scope: [
      'openid',
      'https://www.googleapis.com/auth/userinfo.email',
      'https://www.googleapis.com/auth/userinfo.profile',
      'https://www.googleapis.com/auth/spreadsheets',
      'https://www.googleapis.com/auth/drive.file'
    ].join(' ')
  });
  
  return (
    <Button 
      variant="contained" 
      onClick={() => handleLogin()}
      sx={{
        backgroundColor: '#4285f4',
        color: 'white',
        textTransform: 'none',
        padding: '10px 16px',
        '&:hover': {
          backgroundColor: '#357ae8',
        }
      }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img 
        src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" 
        alt="Google logo" 
        style={{ width: 18, height: 18, marginRight: 8 }}
      />
      Sign in with Google
    </Button>
  );
}


