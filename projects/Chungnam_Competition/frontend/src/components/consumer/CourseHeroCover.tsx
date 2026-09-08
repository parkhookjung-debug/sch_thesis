import { useEffect, useState } from 'react'
import { ImageOff } from 'lucide-react'
import { appImageSrc, COURSE_IMAGE_FALLBACK } from '@/lib/courseImageFallback'

export function CourseHeroCover({ primarySrc }: { primarySrc: string }) {
  const [src, setSrc] = useState(() => appImageSrc(primarySrc))
  const [showImg, setShowImg] = useState(true)

  useEffect(() => {
    setSrc(appImageSrc(primarySrc))
    setShowImg(true)
  }, [primarySrc])

  return (
    <div className="relative aspect-[16/10] w-full overflow-hidden bg-[linear-gradient(135deg,#efe6d8,#e8f3ee_58%,#e7eef8)]">
      {showImg ? (
        <img
          src={src}
          alt=""
          className="w-full h-full object-cover"
          onError={() => {
            if (src !== COURSE_IMAGE_FALLBACK) {
              setSrc(COURSE_IMAGE_FALLBACK)
            } else {
              setShowImg(false)
            }
          }}
        />
      ) : (
        <div className="w-full h-full min-h-[11rem] flex flex-col items-center justify-center gap-2 text-slate-500">
          <ImageOff className="w-10 h-10" strokeWidth={1.5} />
          <span className="text-[12px] font-semibold tracking-wide">코스 이미지 준비 중</span>
        </div>
      )}
      <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-[#2b1b12]/42 to-transparent pointer-events-none" />
    </div>
  )
}
