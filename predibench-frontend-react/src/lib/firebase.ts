import { initializeApp } from 'firebase/app'
import { getAuth } from 'firebase/auth'
import { getFirestore } from 'firebase/firestore'

const firebaseConfig = {
  apiKey: "AIzaSyBDarsWHLp76j1HgSo22mS8JlzR0AtNZ_w",
  authDomain: "predibench.firebaseapp.com",
  projectId: "predibench",
  storageBucket: "predibench.firebasestorage.app",
  messagingSenderId: "273710233257",
  appId: "1:273710233257:web:7a07a9c0d76370d85cdbb8",
  measurementId: "G-KJFQSXN9S9"
}

// Initialize Firebase
const app = initializeApp(firebaseConfig)

// Initialize Firebase Authentication and get a reference to the service
export const auth = getAuth(app)

// Initialize Cloud Firestore and get a reference to the service
export const db = getFirestore(app)

export default app