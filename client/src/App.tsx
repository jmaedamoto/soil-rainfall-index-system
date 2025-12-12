import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import SoilRainfallDashboard from './pages/SoilRainfallDashboard'
import Production from './pages/Production'
import ProductionSession from './pages/ProductionSession'
import RainfallAdjustment from './pages/RainfallAdjustment'
import './App.css'

function App() {
  return (
    <div className="App">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<SoilRainfallDashboard />} />
        <Route path="/production" element={<Production />} />
        <Route path="/production-session" element={<ProductionSession />} />
        <Route path="/rainfall-adjustment" element={<RainfallAdjustment />} />
      </Routes>
    </div>
  )
}

export default App