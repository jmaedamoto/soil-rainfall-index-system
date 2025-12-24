// import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import SoilRainfallDashboard from './pages/SoilRainfallDashboard'
import Production from './pages/Production'
import ProductionSession from './pages/ProductionSession'
import './App.css'

function App() {
  return (
    <div className="App">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<SoilRainfallDashboard />} />
        <Route path="/production" element={<Production />} />
        <Route path="/production-session" element={<ProductionSession />} />
      </Routes>
    </div>
  )
}

export default App