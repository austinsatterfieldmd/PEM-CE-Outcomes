import React, { useState, useCallback, useRef } from 'react';
import { Zap, Upload, FileText, AlertCircle, CheckCircle, Clock, ChevronDown, ChevronUp, Download, Target, BookOpen } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8002/api';

interface QuestionAnalysis {
  question_number: number;
  question_stem: string;
  options: string[];
  correct_answer: string;
  learning_objective: string;
  tags: Record<string, any>;
  qboost_score: number;
  qboost_grade: string;
  qboost_breakdown: Record<string, any>;
  ready_for_deployment: boolean;
  lo_alignment: {
    score: number;
    grade: string;
    assessment: string;
    suggestions: string[];
  } | null;
  cme_level: string;
}

interface AnalysisResult {
  filename: string;
  activity_title: string;
  analysis_timestamp: string;
  total_questions: number;
  avg_qboost_score: number;
  avg_lo_alignment: number;
  grade_distribution: Record<string, number>;
  ready_count: number;
  ready_percentage: number;
  warnings: string[];
  total_cost: number;
  model_used: string;
  questions: QuestionAnalysis[];
}

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-green-100 text-green-800 border-green-200',
  B: 'bg-blue-100 text-blue-800 border-blue-200',
  C: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  D: 'bg-orange-100 text-orange-800 border-orange-200',
  F: 'bg-red-100 text-red-800 border-red-200',
};

const GRADE_BG_COLORS: Record<string, string> = {
  A: 'bg-green-500',
  B: 'bg-blue-500',
  C: 'bg-yellow-500',
  D: 'bg-orange-500',
  F: 'bg-red-500',
};

export default function QBoostTab() {
  const [file, setFile] = useState<File | null>(null);
  const [model, setModel] = useState<string>('gpt');
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [expandedQuestion, setExpandedQuestion] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (!selectedFile.name.endsWith('.docx')) {
        setError('Please select a .docx file');
        return;
      }
      setFile(selectedFile);
      setError(null);
      setResult(null);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      if (!droppedFile.name.endsWith('.docx')) {
        setError('Please select a .docx file');
        return;
      }
      setFile(droppedFile);
      setError(null);
      setResult(null);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  }, []);

  const pollAnalysisStatus = async (analysisId: string) => {
    let attempts = 0;
    const maxAttempts = 120; // 2 minutes max

    while (attempts < maxAttempts) {
      try {
        const response = await fetch(`${API_BASE}/qboost/analysis/${analysisId}`);
        const data = await response.json();

        setProgress(data.progress || 0);

        if (data.status === 'completed') {
          setResult(data.result);
          setAnalyzing(false);
          return;
        } else if (data.status === 'failed') {
          setError(data.message || 'Analysis failed');
          setAnalyzing(false);
          return;
        }

        await new Promise(resolve => setTimeout(resolve, 1000));
        attempts++;
      } catch (err) {
        setError('Error checking analysis status');
        setAnalyzing(false);
        return;
      }
    }

    setError('Analysis timed out');
    setAnalyzing(false);
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);
    setProgress(0);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/qboost/upload?model=${model}`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const data = await response.json();
      setUploading(false);
      setAnalyzing(true);
      setProgress(10);

      // Poll for results
      await pollAnalysisStatus(data.analysis_id);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setUploading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setResult(null);
    setError(null);
    setProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const downloadResults = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `qboost_analysis_${result.filename.replace('.docx', '')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-6 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-white/20 rounded-lg">
            <Zap className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">QBoost</h1>
            <p className="text-purple-100 text-sm">
              Question Quality Analysis & Learning Objective Alignment
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6">
        {!result ? (
          /* Upload Section */
          <div className="max-w-2xl mx-auto">
            {/* Drop Zone */}
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onClick={() => fileInputRef.current?.click()}
              className={`
                border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all
                ${file ? 'border-purple-400 bg-purple-50' : 'border-gray-300 hover:border-purple-400 hover:bg-purple-50'}
              `}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".docx"
                onChange={handleFileSelect}
                className="hidden"
              />

              {file ? (
                <div className="space-y-3">
                  <FileText className="w-16 h-16 mx-auto text-purple-500" />
                  <p className="text-lg font-medium text-gray-900">{file.name}</p>
                  <p className="text-sm text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <Upload className="w-16 h-16 mx-auto text-gray-400" />
                  <p className="text-lg font-medium text-gray-700">
                    Drop your outcomes document here
                  </p>
                  <p className="text-sm text-gray-500">
                    or click to browse (.docx files only)
                  </p>
                </div>
              )}
            </div>

            {/* Model Selection */}
            <div className="mt-6 p-4 bg-white rounded-lg border">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Analysis Model
              </label>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { id: 'gpt', name: 'GPT-5.2', cost: '~$0.02/q' },
                  { id: 'claude', name: 'Claude Opus', cost: '~$0.07/q' },
                  { id: 'gemini', name: 'Gemini 2.5', cost: '~$0.02/q' },
                ].map((m) => (
                  <button
                    key={m.id}
                    onClick={() => setModel(m.id)}
                    className={`
                      p-3 rounded-lg border-2 transition-all text-left
                      ${model === m.id ? 'border-purple-500 bg-purple-50' : 'border-gray-200 hover:border-purple-300'}
                    `}
                  >
                    <div className="font-medium text-gray-900">{m.name}</div>
                    <div className="text-xs text-gray-500">{m.cost}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Error Display */}
            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                <p className="text-red-700">{error}</p>
              </div>
            )}

            {/* Progress Display */}
            {(uploading || analyzing) && (
              <div className="mt-4 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                <div className="flex items-center gap-3 mb-3">
                  <Clock className="w-5 h-5 text-purple-500 animate-pulse" />
                  <span className="text-purple-700 font-medium">
                    {uploading ? 'Uploading...' : `Analyzing questions... ${progress}%`}
                  </span>
                </div>
                <div className="w-full bg-purple-200 rounded-full h-2">
                  <div
                    className="bg-purple-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Upload Button */}
            <div className="mt-6 flex gap-3">
              <button
                onClick={handleUpload}
                disabled={!file || uploading || analyzing}
                className={`
                  flex-1 py-3 px-6 rounded-lg font-medium flex items-center justify-center gap-2 transition-all
                  ${file && !uploading && !analyzing
                    ? 'bg-purple-600 text-white hover:bg-purple-700'
                    : 'bg-gray-200 text-gray-500 cursor-not-allowed'}
                `}
              >
                <Zap className="w-5 h-5" />
                Analyze Document
              </button>
              {file && (
                <button
                  onClick={handleReset}
                  className="py-3 px-6 rounded-lg font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 transition-all"
                >
                  Clear
                </button>
              )}
            </div>

            {/* Instructions */}
            <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h3 className="font-medium text-blue-900 mb-2">How it works</h3>
              <ol className="text-sm text-blue-800 space-y-2 list-decimal list-inside">
                <li>Upload your PER Outcomes Questions Review document (.docx)</li>
                <li>Select the AI model for analysis (GPT-5.2 recommended for cost/quality balance)</li>
                <li>QBoost will tag each question and calculate quality scores</li>
                <li>Learning objective alignment is assessed for each question</li>
                <li>Review results and download the analysis report</li>
              </ol>
            </div>
          </div>
        ) : (
          /* Results Section */
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-5 gap-4">
              <div className="bg-white p-4 rounded-lg border shadow-sm">
                <div className="text-sm text-gray-500 mb-1">Questions</div>
                <div className="text-2xl font-bold text-gray-900">{result.total_questions}</div>
              </div>
              <div className="bg-white p-4 rounded-lg border shadow-sm">
                <div className="text-sm text-gray-500 mb-1">Avg QBoost</div>
                <div className="text-2xl font-bold text-purple-600">{result.avg_qboost_score}</div>
              </div>
              <div className="bg-white p-4 rounded-lg border shadow-sm">
                <div className="text-sm text-gray-500 mb-1">Avg LO Align</div>
                <div className="text-2xl font-bold text-indigo-600">{result.avg_lo_alignment || 'N/A'}</div>
              </div>
              <div className="bg-white p-4 rounded-lg border shadow-sm">
                <div className="text-sm text-gray-500 mb-1">Ready</div>
                <div className="text-2xl font-bold text-green-600">
                  {result.ready_count}/{result.total_questions}
                </div>
              </div>
              <div className="bg-white p-4 rounded-lg border shadow-sm">
                <div className="text-sm text-gray-500 mb-1">Cost</div>
                <div className="text-2xl font-bold text-gray-600">${result.total_cost.toFixed(3)}</div>
              </div>
            </div>

            {/* Grade Distribution */}
            <div className="bg-white p-4 rounded-lg border shadow-sm">
              <h3 className="font-medium text-gray-900 mb-3">Grade Distribution</h3>
              <div className="flex items-end gap-2 h-32">
                {['A', 'B', 'C', 'D', 'F'].map((grade) => {
                  const count = result.grade_distribution[grade] || 0;
                  const pct = result.total_questions > 0 ? (count / result.total_questions) * 100 : 0;
                  return (
                    <div key={grade} className="flex-1 flex flex-col items-center gap-1">
                      <div className="w-full flex flex-col items-center justify-end h-20">
                        <span className="text-xs text-gray-500 mb-1">{count}</span>
                        <div
                          className={`w-full rounded-t ${GRADE_BG_COLORS[grade]} transition-all`}
                          style={{ height: `${Math.max(pct, 4)}%` }}
                        />
                      </div>
                      <span className={`text-sm font-bold px-2 py-0.5 rounded ${GRADE_COLORS[grade]}`}>
                        {grade}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <button
                onClick={downloadResults}
                className="flex items-center gap-2 py-2 px-4 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-all"
              >
                <Download className="w-4 h-4" />
                Download Results
              </button>
              <button
                onClick={handleReset}
                className="py-2 px-4 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-all"
              >
                Analyze Another Document
              </button>
            </div>

            {/* Warnings */}
            {result.warnings.length > 0 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <h3 className="font-medium text-yellow-900 mb-2">Parse Warnings</h3>
                <ul className="text-sm text-yellow-800 space-y-1 list-disc list-inside">
                  {result.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Questions Table */}
            <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
              <div className="p-4 border-b bg-gray-50">
                <h3 className="font-medium text-gray-900">Question Analysis</h3>
              </div>
              <div className="divide-y">
                {result.questions.map((q) => (
                  <div key={q.question_number} className="hover:bg-gray-50 transition-colors">
                    <div
                      className="p-4 cursor-pointer flex items-center gap-4"
                      onClick={() => setExpandedQuestion(
                        expandedQuestion === q.question_number ? null : q.question_number
                      )}
                    >
                      <div className="w-8 h-8 flex items-center justify-center bg-gray-100 rounded-full text-sm font-bold">
                        {q.question_number}
                      </div>

                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-900 truncate">{q.question_stem}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          {q.cme_level} • {q.tags.topic || 'No topic'}
                        </p>
                      </div>

                      {/* QBoost Score */}
                      <div className="flex items-center gap-2">
                        <Zap className="w-4 h-4 text-purple-500" />
                        <span className="text-lg font-bold text-gray-900">{q.qboost_score}</span>
                        <span className={`text-sm font-bold px-2 py-0.5 rounded border ${GRADE_COLORS[q.qboost_grade]}`}>
                          {q.qboost_grade}
                        </span>
                      </div>

                      {/* LO Alignment */}
                      <div className="flex items-center gap-2">
                        <Target className="w-4 h-4 text-indigo-500" />
                        <span className="text-lg font-bold text-gray-900">
                          {q.lo_alignment?.score || 'N/A'}
                        </span>
                        {q.lo_alignment?.grade && (
                          <span className={`text-sm font-bold px-2 py-0.5 rounded border ${GRADE_COLORS[q.lo_alignment.grade] || 'bg-gray-100'}`}>
                            {q.lo_alignment.grade}
                          </span>
                        )}
                      </div>

                      {/* Ready Indicator */}
                      {q.ready_for_deployment ? (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      ) : (
                        <AlertCircle className="w-5 h-5 text-orange-500" />
                      )}

                      {expandedQuestion === q.question_number ? (
                        <ChevronUp className="w-5 h-5 text-gray-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-gray-400" />
                      )}
                    </div>

                    {/* Expanded Details */}
                    {expandedQuestion === q.question_number && (
                      <div className="px-4 pb-4 space-y-4 border-t bg-gray-50">
                        {/* Question Text */}
                        <div className="pt-4">
                          <h4 className="text-sm font-medium text-gray-700 mb-2">Question</h4>
                          <p className="text-sm text-gray-900 whitespace-pre-wrap">{q.question_stem}</p>
                        </div>

                        {/* Answer Options */}
                        <div>
                          <h4 className="text-sm font-medium text-gray-700 mb-2">Options</h4>
                          <div className="space-y-1">
                            {q.options.map((opt, i) => (
                              <p
                                key={i}
                                className={`text-sm p-2 rounded ${
                                  opt.startsWith(q.correct_answer)
                                    ? 'bg-green-100 text-green-800 font-medium'
                                    : 'text-gray-700'
                                }`}
                              >
                                {opt}
                              </p>
                            ))}
                          </div>
                        </div>

                        {/* Learning Objective */}
                        {q.learning_objective && (
                          <div>
                            <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                              <BookOpen className="w-4 h-4" />
                              Learning Objective
                            </h4>
                            <p className="text-sm text-gray-700 bg-indigo-50 p-3 rounded">
                              {q.learning_objective}
                            </p>
                            {q.lo_alignment && (
                              <div className="mt-2 p-3 bg-white rounded border">
                                <p className="text-sm text-gray-900">{q.lo_alignment.assessment}</p>
                                {q.lo_alignment.suggestions.length > 0 && (
                                  <ul className="mt-2 text-sm text-gray-600 list-disc list-inside">
                                    {q.lo_alignment.suggestions.map((s, i) => (
                                      <li key={i}>{s}</li>
                                    ))}
                                  </ul>
                                )}
                              </div>
                            )}
                          </div>
                        )}

                        {/* QBoost Breakdown */}
                        <div>
                          <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                            <Zap className="w-4 h-4" />
                            QBoost Breakdown
                          </h4>
                          <div className="grid grid-cols-3 gap-4 text-sm">
                            {/* Flaws */}
                            <div className="p-3 bg-white rounded border">
                              <div className="font-medium text-red-600 mb-2">Flaw Deductions</div>
                              {Object.entries(q.qboost_breakdown.flaws || {}).map(([key, val]) => (
                                val !== 0 && (
                                  <div key={key} className="flex justify-between text-gray-600">
                                    <span>{key.replace('flaw_', '').replace(/_/g, ' ')}</span>
                                    <span className="font-mono">{val as number}</span>
                                  </div>
                                )
                              ))}
                            </div>
                            {/* Structure Deductions */}
                            <div className="p-3 bg-white rounded border">
                              <div className="font-medium text-orange-600 mb-2">Structure Deductions</div>
                              {Object.entries(q.qboost_breakdown.structure_deductions || {}).map(([key, val]) => (
                                <div key={key} className="flex justify-between text-gray-600">
                                  <span className="truncate">{key.split(':')[1] || key}</span>
                                  <span className="font-mono">{val as number}</span>
                                </div>
                              ))}
                              {Object.keys(q.qboost_breakdown.structure_deductions || {}).length === 0 && (
                                <div className="text-gray-400">None</div>
                              )}
                            </div>
                            {/* Structure Bonuses */}
                            <div className="p-3 bg-white rounded border">
                              <div className="font-medium text-green-600 mb-2">Structure Bonuses</div>
                              {Object.entries(q.qboost_breakdown.structure_bonuses || {}).map(([key, val]) => (
                                <div key={key} className="flex justify-between text-gray-600">
                                  <span className="truncate">{key.split(':')[1] || key}</span>
                                  <span className="font-mono text-green-600">+{val as number}</span>
                                </div>
                              ))}
                              {Object.keys(q.qboost_breakdown.structure_bonuses || {}).length === 0 && (
                                <div className="text-gray-400">None</div>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Tags */}
                        <div>
                          <h4 className="text-sm font-medium text-gray-700 mb-2">Tags</h4>
                          <div className="flex flex-wrap gap-2">
                            {Object.entries(q.tags).filter(([_, v]) => v !== null && v !== false).map(([key, val]) => (
                              <span key={key} className="text-xs bg-gray-200 px-2 py-1 rounded">
                                <span className="text-gray-500">{key}:</span>{' '}
                                <span className="font-medium">{String(val)}</span>
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
