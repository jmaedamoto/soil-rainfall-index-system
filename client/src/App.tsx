// import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProductionSession from './pages/ProductionSession'
import './App.css'

function App() {
  return (
    <div className="App">
      <Routes>
        <Route path="/" element={<Navigate to="/kinki" replace />} />
        <Route path="/kinki" element={<ProductionSession key="kinki" regionCode="kinki" />} />
        <Route path="/chugoku" element={<ProductionSession key="chugoku" regionCode="chugoku" />} />
        <Route path="/shikoku" element={<ProductionSession key="shikoku" regionCode="shikoku" />} />
      </Routes>
    </div>
  )
}

export default App
