import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import SoilRainfallDashboard from './pages/SoilRainfallDashboard'
import './App.css'

function App() {
  return (
    <div className="App">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<SoilRainfallDashboard />} />
      </Routes>
    </div>
  )
}

export default App