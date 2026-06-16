import { useState } from 'react';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

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
      const response = await fetch('http://161.104.50.187:8000/api/v1/moderate', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();

      // НОВАЯ ЛОГИКА: Если сервер вернул ошибку (код 500 или 400)
      if (!response.ok) {
        setResult({
          overall_status: 'error',
          message: data.detail || 'Внутренняя ошибка сервера'
        });
        return;
      }

      setResult(data);
    } catch (error) {
      setResult({
        overall_status: 'error',
        message: 'Сервер недоступен.'
      });
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

const getStatusConfig = (status) => {
    if (status === 'error') return { class: 'status-error', badge: 'badge-error', text: 'ОШИБКА СЕРВЕРА', color: '#ff4d4f' };
    if (status === 'blocked') return { class: 'status-blocked', badge: 'badge-blocked', text: 'ЗАБЛОКИРОВАНО', color: '#dc3545' };
    if (status === 'manual_moderation') return { class: 'status-manual', badge: 'badge-manual', text: 'РУЧНАЯ МОДЕРАЦИЯ', color: '#ffc107' };
    return { class: 'status-ok', badge: 'badge-ok', text: 'ОДОБРЕНО', color: '#28a745' };
  };

  const getCategoryConfig = (category) => {
    switch (category) {
      case 'restricted': return { text: 'ЗАПРЕЩЕНО', badgeClass: 'cat-restricted' };
      case 'competitor': return { text: 'КОНКУРЕНТ', badgeClass: 'cat-competitor' };
      case 'employer': return { text: 'РАЗРЕШЕННОЕ ЛОГО', badgeClass: 'cat-employer' };
      default: return { text: 'НЕИЗВЕСТНО', badgeClass: 'cat-unknown' };
    }
  };

  return (
    <div className="container">
      <h1>LogoSeeker</h1>

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
            {result.overall_status === 'error' 
              ? `ОШИБКА СЕРВЕРА: ${result.message}` 
              : `ВЕРДИКТ: ${getStatusConfig(result.overall_status).text}`}
          </div>
        </div>
      )}

      {preview && result?.overall_status !== 'error' && (
        <div className="analysis-container">
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
                      {logo.best_match !== "unknown" ? logo.best_match : "Логотип"} ({(logo.detector_confidence * 100).toFixed(0)}%)
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
          {result && result.details && result.details.length > 0 && (
            <div className="logo-gallery">
              <h3>Найденные объекты ({result.found_logos})</h3>
              
              {result.details.map((logo, index) => {
                const [x_center, y_center, w, h] = logo.box;
                const verdictConfig = getStatusConfig(logo.verdict);
                const categoryConfig = getCategoryConfig(logo.logo_category);

                const cropStyle = {
                  width: `${(1 / w) * 100}%`,
                  height: `${(1 / h) * 100}%`,
                  left: `-${(x_center - w / 2) / w * 100}%`,
                  top: `-${(y_center - h / 2) / h * 100}%`
                };

                return (
                  <div key={`crop-${index}`} className="logo-card" style={{ borderLeft: `6px solid ${verdictConfig.color}` }}>
                    <div className="crop-window">
                       <img src={preview} alt="crop" style={cropStyle} />
                    </div>
                    
                    <div className="logo-info">
                      <div className="logo-header">
                        <strong>{logo.best_match !== "unknown" ? logo.best_match : "Нераспознан"}</strong>
                        <span className={`badge ${categoryConfig.badgeClass}`}>{categoryConfig.text}</span>
                      </div>

                      <span className={`badge ${verdictConfig.badge}`}>{verdictConfig.text}</span>
                      
                      <div className="stats">
                        <span>YOLO: <b>{(logo.detector_confidence * 100).toFixed(1)}%</b></span>
                        <span>DINO: <b>{(logo.similarity_score * 100).toFixed(1)}%</b></span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;