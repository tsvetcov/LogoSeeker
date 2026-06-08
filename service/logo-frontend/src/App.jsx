import { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('moderate');
  
  // Стейты для модерации
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  // Стейт для истории
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Функции для загрузки фото
  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setPreview(URL.createObjectURL(selectedFile));
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/v1/moderate', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      setResult(data);
    } catch (error) {
      alert("Ошибка при подключении к серверу.");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // Загрузка истории
  const fetchHistory = async () => {
    setLoadingHistory(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/v1/history');
      const data = await response.json();
      setHistory(data);
    } catch (error) {
      console.error("Ошибка загрузки истории:", error);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'history') {
      fetchHistory();
    }
  }, [activeTab]);

  const getStatusConfig = (status) => {
    if (status === 'blocked') return { class: 'status-blocked', badge: 'badge-blocked', text: 'ЗАБЛОКИРОВАНО', color: '#dc3545' };
    if (status === 'manual_moderation') return { class: 'status-manual', badge: 'badge-manual', text: 'РУЧНАЯ МОДЕРАЦИЯ', color: '#ffc107' };
    return { class: 'status-ok', badge: 'badge-ok', text: 'ОДОБРЕНО', color: '#28a745' };
  };
  return (
    <div className="container">
      <h1>LogoSeeker</h1>
      
      {/* Навигация */}
      <div className="nav-tabs">
        <button 
          className={`tab-btn ${activeTab === 'moderate' ? 'active' : ''}`} 
          onClick={() => setActiveTab('moderate')}
        >
          Проверка фото
        </button>
        <button 
          className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`} 
          onClick={() => setActiveTab('history')}
        >
          История проверок
        </button>
      </div>
  

      {/* Вкладка модерации */}
      {activeTab === 'moderate' && (
        <>
          <div className="upload-box">
            <input type="file" accept="image/*" onChange={handleFileChange} />
            <br />
            <button className="btn" onClick={handleUpload} disabled={!file || loading}>
              {loading ? 'Анализ...' : 'Отправить на проверку'}
            </button>
          </div>

          {result && (
            <div className="results">
              <div className={`status-banner ${getStatusConfig(result.overall_status).class}`}>
                Вердикт: {getStatusConfig(result.overall_status).text}
              </div>
            </div>
          )}

          {preview && (
        <div className="analysis-container">
          
          {/* Левая колонка: Исходное фото с рамками */}
          <div className="image-wrapper">
            <div className="image-container">
              <img src={preview} alt="Preview" />
              
              {result?.details?.map((logo, index) => {
                const [x_center, y_center, w, h] = logo.box;
                const config = getStatusConfig(logo.verdict);
                
                const style = {
                  left: `${(x_center - w / 2) * 100}%`,
                  top: `${(y_center - h / 2) * 100}%`,
                  width: `${w * 100}%`,
                  height: `${h * 100}%`,
                  border: `3px solid ${config.color}`,
                };

                return (
                  <div key={index} className="logo-box" style={style}>
                    <div className="logo-label" style={{ backgroundColor: config.color }}>
                      {logo.best_match !== "Unknown" ? logo.best_match : "Логотип"} ({(logo.detector_confidence * 100).toFixed(0)}%)
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Правая колонка: Галерея вырезанных логотипов */}
          {result && result.details && result.details.length > 0 && (
            <div className="logo-gallery">
              <h3>Найденные объекты ({result.found_logos})</h3>
              
              {result.details.map((logo, index) => {
                const [x_center, y_center, w, h] = logo.box;
                const config = getStatusConfig(logo.verdict);

                const cropStyle = {
                  width: `${(1 / w) * 100}%`,
                  height: `${(1 / h) * 100}%`,
                  left: `-${(x_center - w / 2) / w * 100}%`,
                  top: `-${(y_center - h / 2) / h * 100}%`
                };

                return (
                  <div key={`crop-${index}`} className="logo-card" style={{ borderLeft: `6px solid ${config.color}` }}>
                    <div className="crop-window">
                       <img src={preview} alt="crop" style={cropStyle} />
                    </div>
                    
                    <div className="logo-info">
                      <strong>{logo.best_match !== "Unknown" ? logo.best_match : "Нераспознан"}</strong>
                      <span className={`badge ${config.badge}`}>{config.text}</span>
                      
                      <div className="stats">
                        <span>YOLO: <b>{(logo.detector_confidence * 100).toFixed(1)}%</b></span>
                        <span>Сходство: <b>{(logo.similarity_score * 100).toFixed(1)}%</b></span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
        </>
      )}

      {/* Вкладка Истории */}
      {activeTab === 'history' && (
        <div>
          <h2>Последние проверки</h2>
          {loadingHistory ? (
            <p>Загрузка из базы данных...</p>
          ) : (
            <table className="history-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Файл</th>
                  <th>Логотипов</th>
                  <th>Точное совпадение</th>
                  <th>Статус</th>
                  <th>Дата</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item) => (
                  <tr key={item.id}>
                    <td>#{item.id}</td>
                    <td>{item.filename}</td>
                    <td>{item.found_logos}</td>
                    <td>{item.best_match !== "Unknown" ? item.best_match : "-"}</td>
                    <td>
                      <span className={`badge ${getStatusConfig(item.overall_status).badge}`}>
                        {getStatusConfig(item.overall_status).text}
                      </span>
                    </td>
                    <td>{new Date(item.created_at).toLocaleString('ru-RU')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

export default App;