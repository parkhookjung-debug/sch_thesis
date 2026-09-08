import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './index.css'
import HomePage from '@/pages/HomePage'
import ConsumerResultPage from '@/pages/ConsumerResultPage'
import CourseDetailPage from '@/pages/CourseDetailPage'
import MoreCoursesPage from '@/pages/MoreCoursesPage'
import ReconfigureCoursePage from '@/pages/ReconfigureCoursePage'
import AdminPassQuestMockPage from '@/pages/AdminPassQuestMockPage'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/result" element={<ConsumerResultPage />} />
        <Route path="/result/course" element={<CourseDetailPage />} />
        <Route path="/result/more" element={<MoreCoursesPage />} />
        <Route path="/result/edit" element={<ReconfigureCoursePage />} />
        <Route path="/result/reconfigure" element={<ReconfigureCoursePage />} />
        <Route path="/admin/pass-quest-mock" element={<AdminPassQuestMockPage />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
