// import React from 'react'
import { Routes, Route } from 'react-router-dom'
import ProductionSession from './pages/ProductionSession'
import './App.css'

function App() {
  return (
    <div className="App">
      <Routes>
        <Route path="/" element={<ProductionSession />} />
      </Routes>
    </div>
  )
}

export default App
