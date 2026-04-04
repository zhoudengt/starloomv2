import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { fetchReport } from '../api/reports'
import MarkdownReport from '../components/MarkdownReport'
import { resolveReportGenderFromInput, sectionImagesForReportType } from '../utils/reportSectionImages'
import ReportCertificateHeader from '../components/ReportCertificateHeader'
import { Skeleton } from '../components/Skeleton'
import { StarryBackground } from '../components/StarryBackground'

export default function ReportView() {
  const { reportId } = useParams<{ reportId: string }>()
  const { data, isLoading, error } = useQuery({
    queryKey: ['report', reportId],
    queryFn: () => fetchReport(reportId!),
    enabled: !!reportId,
  })

  if (isLoading) {
    return (
      <>
        <StarryBackground />
        <div className="space-y-3 px-1">
          <Skeleton className="h-8 w-40" />
          <Skeleton className="h-32 w-full rounded-2xl" />
          <Skeleton className="h-48 w-full rounded-2xl" />
        </div>
      </>
    )
  }
  if (error || !data) {
    return (
      <>
        <StarryBackground />
        <p className="text-center text-red-300">报告不存在或无权查看</p>
        <Link to="/my-reports" className="mt-4 block text-center text-[var(--color-brand-gold)]">
          返回列表
        </Link>
      </>
    )
  }

  const sectionImages = sectionImagesForReportType(data.report_type)
  const reportGender = resolveReportGenderFromInput(data.input_data)

  return (
    <>
      <StarryBackground />
      <Link
        to="/my-reports"
        className="mb-4 inline-flex items-center gap-1 text-sm text-[var(--color-brand-gold)]"
      >
        ← 我的报告
      </Link>
      <MarkdownReport
        content={data.content}
        sectionImages={sectionImages}
        gender={reportGender}
        header={
          <ReportCertificateHeader
            badge="StarLoom Archive"
            title={`${data.report_type} · ${data.sign}`}
            lines={[data.created_at ? `生成时间 ${data.created_at}` : '历史报告']}
          />
        }
      />
    </>
  )
}
