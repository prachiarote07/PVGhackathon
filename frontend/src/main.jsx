import React from 'react';
import { createRoot } from 'react-dom/client';
import AccountShell from './api/AccountShell.jsx';
import './styles.css';
import './mobile.css';
import './account.css';
import './product.css';
createRoot(document.getElementById('root')).render(<React.StrictMode><AccountShell /></React.StrictMode>);
