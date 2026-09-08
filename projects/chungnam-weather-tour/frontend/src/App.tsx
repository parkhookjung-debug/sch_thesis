import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import WeatherHeader from '@/components/WeatherHeader'
import ScoreBar from '@/components/ScoreBar'
import DestinationCard from '@/components/DestinationCard'
import CardSkeleton from '@/components/CardSkeleton'
import CoursePanel from '@/components/CoursePanel'
import { useRecommend } from '@/hooks/useRecommend'
import { useCourse } from '@/hooks/useCourse'
import { getTheme } from '@/lib/weather'
import type { Destination } from '@/types'

const PAGE_SIZE = 8

const THEME_BG: Record<string, string> = {
  sunny:  'bg-amber-50',
  cloudy: 'bg-slate-100',
  rainy:  'bg-blue-50',
}

export default function App() {
  const [city, setCity] = useState('전체')
  const [shown, setShown] = useState<Destination[]>([])
  const [selectedDest, setSelectedDest] = useState<Destination | null>(null)
  const { data, loading, error, fetch } = useRecommend()
  const course = useCourse()

  useEffect(() => { fetch(city) }, [city, fetch])
  useEffect(() => {
    if (data) setShown(data.recommendations.slice(0, PAGE_SIZE))
  }, [data])

  const theme = data ? getTheme(data.weather.sky, data.weather.precip_prob) : 'sunny'

  function handleCityChange(next: string | null) {
    if (!next) return
    setCity(next)
    setShown([])
    setSelectedDest(null)
    course.clear()
  }

  function loadMore() {
    if (!data) return
    setShown(data.recommendations.slice(0, shown.length + PAGE_SIZE))
  }

  function handleNextCourse(dest: Destination) {
    if (selectedDest?.name === dest.name) {
      setSelectedDest(null)
      course.clear()
      return
    }
    setSelectedDest(dest)
    const coords = dest.coords
    if (coords) {
      course.fetchFirst(coords.lat, coords.lng, dest.name)
    }
  }

  function handleCourseClose() {
    setSelectedDest(null)
    course.clear()
  }

  return (
    <div className={`min-h-screen transition-colors duration-700 ${THEME_BG[theme]}`}>
      {/* 히어로 헤더 */}
      <WeatherHeader
        city={city}
        weather={data?.weather ?? null}
        theme={theme}
        onCityChange={handleCityChange}
      />

      {/* 점수 게이지 바 */}
      {data && !loading && (
        <div className="sticky top-0 z-10">
          <ScoreBar scores={data.scores} total={data.total_fetched} />
        </div>
      )}

      {/* 본문 */}
      <main className="max-w-2xl mx-auto px-4 py-5 pb-16">
        <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-widest mb-4">
          오늘의 추천 여행지
        </p>

        {loading ? (
          <div className="flex flex-col gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <CardSkeleton key={i} />
            ))}
          </div>
        ) : error ? (
          <div className="text-center py-20 text-muted-foreground">
            <p className="text-5xl mb-4">😓</p>
            <p className="text-sm">{error}</p>
          </div>
        ) : shown.length === 0 ? (
          <div className="text-center py-20 text-muted-foreground">
            <p className="text-5xl mb-4">🗺️</p>
            <p className="text-sm">추천 장소가 없습니다.</p>
          </div>
        ) : (
          <>
            {/* 1위 피처드 카드 */}
            <DestinationCard
              destination={shown[0]}
              rank={1}
              onNextCourse={handleNextCourse}
              isSelected={selectedDest?.name === shown[0].name}
            />
            {selectedDest?.name === shown[0].name && (
              <CoursePanel
                chain={course.chain}
                onSelectCategory={course.selectCategory}
                onSelectPlace={course.selectPlace}
                onClose={handleCourseClose}
              />
            )}

            {/* 2위~ 컴팩트 카드 */}
            {shown.length > 1 && (
              <div className="flex flex-col gap-3">
                {shown.slice(1).map((d, i) => (
                  <div key={d.name}>
                    <DestinationCard
                      destination={d}
                      rank={i + 2}
                      onNextCourse={handleNextCourse}
                      isSelected={selectedDest?.name === d.name}
                    />
                    {selectedDest?.name === d.name && (
                      <CoursePanel
                        chain={course.chain}
                        onSelectCategory={course.selectCategory}
                        onSelectPlace={course.selectPlace}
                        onClose={handleCourseClose}
                      />
                    )}
                  </div>
                ))}
              </div>
            )}

            {data && shown.length < data.recommendations.length && (
              <Button
                variant="outline"
                className="w-full mt-5 rounded-2xl font-semibold bg-white/60 hover:bg-white"
                onClick={loadMore}
              >
                더보기 ({shown.length}/{data.recommendations.length}개)
              </Button>
            )}
          </>
        )}
      </main>
    </div>
  )
}
