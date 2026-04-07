import { useState } from 'react'

function App(): JSX.Element {
  const [count, setCount] = useState(0)

  return (
    <div className="App">
      <h1>ReviewForge</h1>
      <div className="card">
        <button onClick={() => setCount((c) => c + 1)}>count is {count}</button>
        <p>
          Edit <code>src/renderer/src/App.tsx</code> and save to test HMR
        </p>
      </div>
    </div>
  )
}

export default App
