import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import {Provider} from 'react-redux';
import store from './redux/store/store'
import axios from 'axios';
import config from './utils/config';
import { getToken } from './utils/authToken';

// Set default Authorization header. getToken() refuses to hand back an expired
// token (and drops it), so a months-old session can't poison every request the
// app makes — see utils/authToken.js.
const bootToken = getToken();
axios.defaults.headers.common['Authorization'] = bootToken ? `Bearer ${bootToken}` : '';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <Provider store={store}>
    <App />
  </Provider>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
