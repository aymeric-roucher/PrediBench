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

const app = initializeApp(firebaseConfig)
export const auth = getAuth(app)
export const db = getFirestore(app)
export default app